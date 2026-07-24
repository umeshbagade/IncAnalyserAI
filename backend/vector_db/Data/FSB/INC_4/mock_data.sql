-- =====================================================================
--  Mock data for incident: FSB_TSY_DATAHUB_SNAPSHOT_PIPELINE_FAILURE
--  Domain      : FSB (Firm-wide Structural Balance-sheet reporting)
--  Feed        : TSY_LIQUIDITY_BUFFER  (Treasury Liquidity Buffer trades)
--  Report      : Treasury_Liquidity_Buffer_Report  (Saturn / Tableau)
--  COB dates   : 2025-11-13 (13-Nov, healthy baseline)
--                2025-11-14 (14-Nov, INCIDENT COB)
--
--  Pipeline (data flows top -> bottom; RCA investigates bottom -> top):
--
--      PE Ingestion (Oracle staging)      oracle_fsb_staging.tsy_liquidity_buffer
--              |   ingestion_status = SUCCESS  (250 trades / COB)   <-- HEALTHY
--              v
--      Treasury Data Hub Snapshot         dh.snapshot_tsy_liquidity_buffer
--              |   snapshot_status = FAILED (14-Nov, only 180/250)  <-- ROOT CAUSE
--              v
--      Saturn Report (Tableau)            tableau.report_tsy_liquidity_buffer
--                  report_status = PUBLISHED but UNDERSTATED (14-Nov)
--
--  ROOT CAUSE:
--    PE Ingestion completed successfully and loaded all 250 expected trades
--    into staging for both COBs. On 2025-11-14 the Treasury Data Hub snapshot
--    pipeline FAILED before completion: only 180 of the 250 staged trades were
--    written, snapshot_status = FAILED and approval_status = REJECTED. Saturn
--    faithfully consumed that incomplete snapshot and published an understated
--    Liquidity Buffer report (missing 70 trades). Saturn itself has no defect.
--
--  Investigation must STOP at the Data Hub layer: the discrepancy Saturn sees
--  (70 missing trades / understated buffer) EXACTLY equals the trades missing
--  from the Data Hub snapshot versus staging. Because staging is proven
--  complete and healthy, there is nothing to investigate in PE Ingestion.
--
--  Recommended UI incident text (so the RCA engine matches THIS runbook case):
--    Title:       "Saturn Treasury Liquidity Buffer report understated for 14-Nov"
--    Description: "Treasury Data Hub snapshot pipeline failure — an incomplete /
--                  partial snapshot was published for COB 2025-11-14 and Saturn
--                  consumed it, producing an incorrect Liquidity Buffer report."
--
--  Design guarantee:
--    Only the PE Ingestion (staging) rows are generated as the source of truth.
--    The Data Hub snapshot and the Saturn report are DERIVED from staging by
--    SQL, so there are provably no hidden transformations between layers and
--    the ONLY difference on 14-Nov is the 70 trades dropped by the failed
--    snapshot pipeline.
--
--  Dialect: PostgreSQL-compatible (generate_series + window functions).
-- =====================================================================


-- =====================================================================
--  1. CREATE TABLE statements
-- =====================================================================

CREATE SCHEMA IF NOT EXISTS oracle_fsb_staging;  -- oracle.fsb_staging.<feed>_<cob>
CREATE SCHEMA IF NOT EXISTS dh;                  -- Treasury Data Hub snapshots
CREATE SCHEMA IF NOT EXISTS tableau;             -- Saturn reporting (Tableau extract)

-- ---------------------------------------------------------------------
-- PE Ingestion (Oracle staging)  ->  oracle.fsb_staging.<feed>_<cob>
--   In production this is one table per (feed, cob); the mock keeps a
--   `cob_date` column to represent the partition key.
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS oracle_fsb_staging.tsy_liquidity_buffer;
CREATE TABLE oracle_fsb_staging.tsy_liquidity_buffer (
    feed_name         VARCHAR(48)   NOT NULL,
    cob_date          DATE          NOT NULL,   -- partition key (Close-of-Business)
    trade_id          VARCHAR(32)   NOT NULL,
    account_id        VARCHAR(16)   NOT NULL,
    book_id           VARCHAR(16)   NOT NULL,
    counterparty      VARCHAR(48)   NOT NULL,
    currency          VARCHAR(3)    NOT NULL,
    amount            NUMERIC(18,2) NOT NULL,
    business_date     DATE          NOT NULL,
    snapshot_version  VARCHAR(24)   NOT NULL,   -- source extract version tag
    pipeline_run_id   VARCHAR(32)   NOT NULL,
    load_timestamp    TIMESTAMP     NOT NULL,
    ingestion_status  VARCHAR(16)   NOT NULL,   -- 'SUCCESS' for every row (healthy)
    CONSTRAINT pk_stg_tsy_liq PRIMARY KEY (cob_date, trade_id)
);

-- ---------------------------------------------------------------------
-- Treasury Data Hub Snapshot  ->  dh.snapshot_<feed>_<cob>
--   Trade-level snapshot that Saturn consumes. Carries the pipeline
--   status and the approval workflow decision.
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS dh.snapshot_tsy_liquidity_buffer;
CREATE TABLE dh.snapshot_tsy_liquidity_buffer (
    feed_name         VARCHAR(48)   NOT NULL,
    cob_date          DATE          NOT NULL,
    trade_id          VARCHAR(32)   NOT NULL,
    account_id        VARCHAR(16)   NOT NULL,
    book_id           VARCHAR(16)   NOT NULL,
    counterparty      VARCHAR(48)   NOT NULL,
    currency          VARCHAR(3)    NOT NULL,
    amount            NUMERIC(18,2) NOT NULL,
    business_date     DATE          NOT NULL,
    snapshot_version  VARCHAR(24)   NOT NULL,
    pipeline_run_id   VARCHAR(32)   NOT NULL,
    load_timestamp    TIMESTAMP     NOT NULL,
    snapshot_status   VARCHAR(16)   NOT NULL,   -- 'COMPLETED' | 'FAILED'
    approval_status   VARCHAR(16)   NOT NULL,   -- 'APPROVED'  | 'REJECTED'
    CONSTRAINT pk_dh_tsy_liq PRIMARY KEY (cob_date, trade_id)
);

-- ---------------------------------------------------------------------
-- Saturn Report (Tableau)  ->  tableau.report_<name>_<cob>
--   Aggregated Liquidity Buffer report per (cob, currency), inherited
--   1:1 from whatever the Data Hub snapshot contained.
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS tableau.report_tsy_liquidity_buffer;
CREATE TABLE tableau.report_tsy_liquidity_buffer (
    report_name       VARCHAR(64)   NOT NULL,
    cob_date          DATE          NOT NULL,
    currency          VARCHAR(3)    NOT NULL,
    trade_count       INT           NOT NULL,   -- number of trades in the report line
    total_amount      NUMERIC(20,2) NOT NULL,   -- Liquidity Buffer total for the line
    business_date     DATE          NOT NULL,
    snapshot_version  VARCHAR(24)   NOT NULL,
    pipeline_run_id   VARCHAR(32)   NOT NULL,
    load_timestamp    TIMESTAMP     NOT NULL,
    report_status     VARCHAR(16)   NOT NULL,   -- 'PUBLISHED' (Saturn ran fine)
    CONSTRAINT pk_rpt_tsy_liq PRIMARY KEY (cob_date, currency)
);


-- =====================================================================
--  2. INSERT statements
-- =====================================================================
-- =====================================================================
--  2a. PE Ingestion (staging) — HEALTHY source of truth.
--      250 trades per COB for BOTH 13-Nov and 14-Nov = 500 rows total.
--      Every row ingestion_status = 'SUCCESS'. No gaps, no failures.
--
--      Values are deterministic (derived from the trade sequence g) so the
--      whole dataset is reproducible: trade_id, account_id, book_id,
--      counterparty, currency and amount are all a pure function of g, and
--      are IDENTICAL across the two COBs. That makes the day-over-day
--      comparison exact — the ONLY thing that differs on 14-Nov is which
--      trades survive into the snapshot.
-- =====================================================================
INSERT INTO oracle_fsb_staging.tsy_liquidity_buffer
(feed_name, cob_date, trade_id, account_id, book_id, counterparty, currency, amount,
 business_date, snapshot_version, pipeline_run_id, load_timestamp, ingestion_status)
SELECT
    'TSY_LIQUIDITY_BUFFER'                                              AS feed_name,
    c.cob_date                                                         AS cob_date,
    'TRD-' || TO_CHAR(c.cob_date, 'YYYYMMDD') || '-' || LPAD(g::text, 4, '0') AS trade_id,
    'ACC-' || LPAD(((g % 40) + 1)::text, 4, '0')                       AS account_id,
    'BK-'  || LPAD(((g % 12) + 1)::text, 3, '0')                       AS book_id,
    (ARRAY['Goldman Sachs','JP Morgan','Barclays','Deutsche Bank','HSBC',
           'Citibank','BNP Paribas','UBS','Morgan Stanley','Nomura'])[(g % 10) + 1] AS counterparty,
    (ARRAY['USD','USD','USD','EUR','GBP','JPY'])[(g % 6) + 1]          AS currency,
    ROUND((250000 + ((g * 7919) % 4750000))::numeric, 2)              AS amount,
    c.cob_date                                                        AS business_date,
    'PE-EXTRACT-v1'                                                    AS snapshot_version,
    'PE-RUN-' || TO_CHAR(c.cob_date, 'YYYYMMDD')                       AS pipeline_run_id,
    (c.cob_date + TIME '02:00:00' + (g * INTERVAL '7 seconds'))        AS load_timestamp,
    'SUCCESS'                                                          AS ingestion_status
FROM (VALUES (DATE '2025-11-13'), (DATE '2025-11-14')) AS c(cob_date)
CROSS JOIN generate_series(1, 250) AS g;


-- =====================================================================
--  2b. Treasury Data Hub snapshot — DERIVED from staging.
--
--      13-Nov (healthy): ALL 250 trades written.
--                        snapshot_status = 'COMPLETED', approval = 'APPROVED'.
--
--      14-Nov (INCIDENT): the snapshot pipeline FAILED before completion, so
--                        only the first 180 trades were written (trades whose
--                        sequence > 180 were never flushed). The partial
--                        snapshot is stamped snapshot_status = 'FAILED' and the
--                        completeness gate set approval_status = 'REJECTED'.
--
--      => 70 trades (seq 181..250) exist in staging on 14-Nov but are MISSING
--         from the snapshot. That is the entire root cause.
-- =====================================================================
INSERT INTO dh.snapshot_tsy_liquidity_buffer
(feed_name, cob_date, trade_id, account_id, book_id, counterparty, currency, amount,
 business_date, snapshot_version, pipeline_run_id, load_timestamp, snapshot_status, approval_status)
SELECT
    s.feed_name,
    s.cob_date,
    s.trade_id,
    s.account_id,
    s.book_id,
    s.counterparty,
    s.currency,
    s.amount,
    s.business_date,
    CASE WHEN s.cob_date = DATE '2025-11-14' THEN 'DH-SNAP-v1-PARTIAL'
         ELSE 'DH-SNAP-v1' END                                        AS snapshot_version,
    'DH-RUN-' || TO_CHAR(s.cob_date, 'YYYYMMDD')                       AS pipeline_run_id,
    (s.cob_date + TIME '03:10:00')                                     AS load_timestamp,
    CASE WHEN s.cob_date = DATE '2025-11-14' THEN 'FAILED'
         ELSE 'COMPLETED' END                                         AS snapshot_status,
    CASE WHEN s.cob_date = DATE '2025-11-14' THEN 'REJECTED'
         ELSE 'APPROVED' END                                          AS approval_status
FROM oracle_fsb_staging.tsy_liquidity_buffer s
WHERE NOT (
    s.cob_date = DATE '2025-11-14'
    AND CAST(RIGHT(s.trade_id, 4) AS INT) > 180   -- 70 trades lost by the failed snapshot pipeline
);


-- =====================================================================
--  2c. Saturn report — DERIVED from the Data Hub snapshot (1:1, no logic).
--
--      Saturn simply aggregates whatever the snapshot contained, per
--      (cob, currency). It ran to completion (report_status = 'PUBLISHED')
--      on BOTH days — Saturn has NO defect. On 14-Nov the report is
--      understated purely because it consumed the incomplete snapshot.
-- =====================================================================
INSERT INTO tableau.report_tsy_liquidity_buffer
(report_name, cob_date, currency, trade_count, total_amount,
 business_date, snapshot_version, pipeline_run_id, load_timestamp, report_status)
SELECT
    'Treasury_Liquidity_Buffer_Report'                                AS report_name,
    d.cob_date,
    d.currency,
    COUNT(*)                                                          AS trade_count,
    SUM(d.amount)                                                     AS total_amount,
    d.business_date,
    d.snapshot_version,
    'SAT-RUN-' || TO_CHAR(d.cob_date, 'YYYYMMDD')                     AS pipeline_run_id,
    (d.cob_date + TIME '04:05:00')                                    AS load_timestamp,
    'PUBLISHED'                                                       AS report_status
FROM dh.snapshot_tsy_liquidity_buffer d
GROUP BY d.cob_date, d.currency, d.business_date, d.snapshot_version;


-- =====================================================================
--  3. Compare Saturn report against the Data Hub snapshot.
--
--     STEP 1 of the investigation. The report totals must EXACTLY equal the
--     snapshot aggregates on both days (delta = 0). This proves Saturn is a
--     faithful mirror of the snapshot and has no calculation defect — so the
--     investigation moves DOWN to the Data Hub layer.
-- =====================================================================
WITH snap_agg AS (
    SELECT cob_date, currency, COUNT(*) AS snap_trades, SUM(amount) AS snap_total
    FROM dh.snapshot_tsy_liquidity_buffer
    GROUP BY cob_date, currency
)
SELECT
    r.cob_date,
    r.currency,
    r.trade_count                          AS report_trades,
    s.snap_trades,
    (r.trade_count - s.snap_trades)        AS trade_delta,      -- expect 0
    r.total_amount                         AS report_total,
    s.snap_total,
    (r.total_amount - s.snap_total)        AS amount_delta      -- expect 0.00
FROM tableau.report_tsy_liquidity_buffer r
JOIN snap_agg s
  ON s.cob_date = r.cob_date AND s.currency = r.currency
ORDER BY r.cob_date, r.currency;


-- =====================================================================
--  4. Prove the Data Hub snapshot is INCOMPLETE (vs. healthy staging).
--
--     STEP 2 of the investigation. Staging (PE Ingestion) is complete on both
--     COBs (250 trades). The snapshot matches staging on 13-Nov (250) but is
--     short by 70 on 14-Nov (180) — the missing-trade count that exactly
--     explains the Saturn understatement.
-- =====================================================================
-- 4a. Row-count reconciliation: staging vs snapshot, per COB.
SELECT
    stg.cob_date,
    stg.staging_trades,                                 -- expect 250 both days
    COALESCE(snp.snapshot_trades, 0)          AS snapshot_trades,   -- 250 / 180
    stg.staging_trades - COALESCE(snp.snapshot_trades, 0) AS missing_trades,  -- 0 / 70
    stg.staging_status,                                 -- SUCCESS both days
    COALESCE(snp.snapshot_status, 'NONE')     AS snapshot_status,   -- COMPLETED / FAILED
    COALESCE(snp.approval_status, 'NONE')     AS approval_status    -- APPROVED / REJECTED
FROM (
    SELECT cob_date, COUNT(*) AS staging_trades, MAX(ingestion_status) AS staging_status
    FROM oracle_fsb_staging.tsy_liquidity_buffer
    GROUP BY cob_date
) stg
LEFT JOIN (
    SELECT cob_date, COUNT(*) AS snapshot_trades,
           MAX(snapshot_status) AS snapshot_status,
           MAX(approval_status) AS approval_status
    FROM dh.snapshot_tsy_liquidity_buffer
    GROUP BY cob_date
) snp
  ON snp.cob_date = stg.cob_date
ORDER BY stg.cob_date;

-- 4b. The exact 70 trades present in staging but MISSING from the snapshot on
--     14-Nov (anti-join). These are precisely the trades absent from Saturn.
SELECT
    s.cob_date,
    s.trade_id,
    s.account_id,
    s.book_id,
    s.counterparty,
    s.currency,
    s.amount,
    s.ingestion_status                        -- SUCCESS: proven loaded upstream
FROM oracle_fsb_staging.tsy_liquidity_buffer s
WHERE s.cob_date = DATE '2025-11-14'
  AND NOT EXISTS (
      SELECT 1
      FROM dh.snapshot_tsy_liquidity_buffer d
      WHERE d.cob_date = s.cob_date
        AND d.trade_id = s.trade_id
  )
ORDER BY s.trade_id;

-- 4c. Magnitude of the gap: buffer amount dropped by the failed snapshot.
SELECT
    'Buffer amount lost to incomplete snapshot (COB 2025-11-14)' AS description,
    (SELECT SUM(amount) FROM oracle_fsb_staging.tsy_liquidity_buffer
      WHERE cob_date = DATE '2025-11-14')                          AS staging_total,
    (SELECT SUM(amount) FROM dh.snapshot_tsy_liquidity_buffer
      WHERE cob_date = DATE '2025-11-14')                          AS snapshot_total,
    (SELECT SUM(amount) FROM oracle_fsb_staging.tsy_liquidity_buffer
      WHERE cob_date = DATE '2025-11-14')
      - (SELECT SUM(amount) FROM dh.snapshot_tsy_liquidity_buffer
          WHERE cob_date = DATE '2025-11-14')                       AS understated_by;


-- =====================================================================
--  5. Show the snapshot pipeline FAILURE / approval REJECTION directly.
--
--     This is the smoking gun at the Data Hub layer. Once this is seen the
--     investigation STOPS — the root cause is identified and there is no
--     reason to drill into PE Ingestion (staging is complete + SUCCESS).
-- =====================================================================
-- 5a. Snapshot run status per COB.
SELECT
    cob_date,
    MAX(snapshot_status)  AS snapshot_status,     -- 2025-11-14 => FAILED
    MAX(approval_status)  AS approval_status,      -- 2025-11-14 => REJECTED
    MAX(snapshot_version) AS snapshot_version,      -- 2025-11-14 => *-PARTIAL
    COUNT(*)              AS trades_written
FROM dh.snapshot_tsy_liquidity_buffer
GROUP BY cob_date
ORDER BY cob_date;

-- 5b. Explicit failed / rejected snapshot rows (the incident COB).
SELECT DISTINCT
    feed_name, cob_date, snapshot_status, approval_status, snapshot_version, pipeline_run_id
FROM dh.snapshot_tsy_liquidity_buffer
WHERE snapshot_status = 'FAILED'
   OR approval_status = 'REJECTED';

-- 5c. Confirm PE Ingestion is HEALTHY (so we correctly stop and do NOT
--     investigate it): all staging rows for the incident COB are SUCCESS.
SELECT
    cob_date,
    ingestion_status,
    COUNT(*) AS trades
FROM oracle_fsb_staging.tsy_liquidity_buffer
WHERE cob_date = DATE '2025-11-14'
GROUP BY cob_date, ingestion_status;   -- single row: SUCCESS, 250


-- =====================================================================
--  6. Root-cause summary
-- =====================================================================
--  Root Cause: Treasury Data Hub Snapshot Pipeline Failure. An incomplete
--  snapshot was published (180 of 250 trades for COB 2025-11-14, with
--  snapshot_status = FAILED and approval_status = REJECTED), which propagated
--  to Saturn reporting and produced an understated Treasury Liquidity Buffer
--  report. Since the root cause was identified at Data Hub — and PE Ingestion
--  staging is proven complete and healthy (250 trades, ingestion_status =
--  SUCCESS) — no further investigation into PE Ingestion is required.
--
--  Evidence chain:
--    * Query 3  : Saturn report == Data Hub snapshot (delta 0)  -> Saturn OK.
--    * Query 4a : staging 250 vs snapshot 180 on 14-Nov         -> 70 missing.
--    * Query 4b : the exact 70 missing trades (all SUCCESS in staging).
--    * Query 5a/5b : snapshot_status = FAILED, approval = REJECTED.
--    * Query 5c : PE Ingestion staging fully SUCCESS             -> stop here.
-- =====================================================================
