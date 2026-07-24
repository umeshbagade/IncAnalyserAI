-- =====================================================================
--  Mock data for incident: FSB report generation failure  (FSB / INC_1)
--  Domain      : FSB (Firm-wide Structural Balance-sheet reporting)
--  Flow        : fsb_reporting  (Monthly: PE Ingest -> Data Hub DQ/snapshot -> Saturn report)
--  Feed        : FSB_BALANCE_SHEET
--  Report      : FSB_Regulatory_Report  (Saturn / Tableau)
--  COB dates   : 2025-10-31 (Oct month-end, healthy baseline)
--                2025-11-30 (Nov month-end, INCIDENT COB)
--
--  ROOT CAUSE : Treasury Data Hub Monthly SNAPSHOT PIPELINE FAILURE.
--
--  Pipeline (data flows top -> bottom; RCA investigates bottom -> top):
--
--      PE Ingestion (Oracle staging)      oracle_pe_fsb_staging.fsb_balance_sheet
--              |   ingestion_status = SUCCESS  (300 rows / COB)     <-- HEALTHY
--              v
--      Treasury Data Hub Snapshot         dh.snapshot_fsb_balance_sheet
--              |   snapshot_status = FAILED (30-Nov, only 210/300)  <-- ROOT CAUSE
--              v
--      Saturn Report (Tableau)            tableau.report_fsb_regulatory
--                  report_status = PUBLISHED but UNDERSTATED (30-Nov)
--
--  WHY THE ISSUE IS AT DATA HUB (NOT INGESTION):
--    PE Ingestion completed successfully and loaded all 300 expected rows into
--    staging for BOTH month-ends. On 2025-11-30 the Data Hub Monthly snapshot
--    pipeline FAILED before completion: only 210 of the 300 staged rows were
--    written, snapshot_status = FAILED and approval_status = REJECTED. Saturn
--    faithfully consumed that incomplete snapshot and published an understated
--    FSB report (missing 90 rows). Saturn itself has no defect, and PE
--    Ingestion staging is provably complete — so the investigation must STOP
--    at the Data Hub layer and NOT drill into ingestion.
--
--  Design guarantee:
--    Only the PE Ingestion (staging) rows are generated as the source of truth.
--    The Data Hub snapshot and the Saturn report are DERIVED from staging by
--    SQL, so there are provably no hidden transformations between layers and
--    the ONLY difference on 30-Nov is the 90 rows dropped by the failed
--    snapshot pipeline.
--
--  Dialect: PostgreSQL-compatible (generate_series + window functions).
-- =====================================================================


-- =====================================================================
--  1. CREATE TABLE statements
-- =====================================================================

CREATE SCHEMA IF NOT EXISTS oracle_pe_fsb_staging;  -- oracle.pe_fsb_staging.<feed>_<cob>
CREATE SCHEMA IF NOT EXISTS dh;                     -- Treasury Data Hub snapshots
CREATE SCHEMA IF NOT EXISTS tableau;                -- Saturn reporting (Tableau extract)

-- ---------------------------------------------------------------------
-- PE Ingestion (Oracle staging)  ->  oracle.pe_fsb_staging.<feed>_<cob>
--   In production this is one table per (feed, cob); the mock keeps a
--   `cob_date` column to represent the partition key.
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS oracle_pe_fsb_staging.fsb_balance_sheet;
CREATE TABLE oracle_pe_fsb_staging.fsb_balance_sheet (
    feed_name         VARCHAR(48)   NOT NULL,
    cob_date          DATE          NOT NULL,   -- partition key (Close-of-Business, month-end)
    position_id       VARCHAR(32)   NOT NULL,
    account_id        VARCHAR(16)   NOT NULL,
    book_id           VARCHAR(16)   NOT NULL,
    legal_entity      VARCHAR(48)   NOT NULL,
    currency          VARCHAR(3)    NOT NULL,
    amount            NUMERIC(18,2) NOT NULL,
    business_date     DATE          NOT NULL,
    snapshot_version  VARCHAR(24)   NOT NULL,   -- source extract version tag
    pipeline_run_id   VARCHAR(32)   NOT NULL,
    load_timestamp    TIMESTAMP     NOT NULL,
    ingestion_status  VARCHAR(16)   NOT NULL,   -- 'SUCCESS' for every row (healthy)
    CONSTRAINT pk_stg_fsb_bs PRIMARY KEY (cob_date, position_id)
);

-- ---------------------------------------------------------------------
-- Treasury Data Hub Snapshot  ->  dh.snapshot_<feed>_<cob>
--   Position-level snapshot that Saturn consumes. Carries the pipeline
--   status and the approval workflow decision.
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS dh.snapshot_fsb_balance_sheet;
CREATE TABLE dh.snapshot_fsb_balance_sheet (
    feed_name         VARCHAR(48)   NOT NULL,
    cob_date          DATE          NOT NULL,
    position_id       VARCHAR(32)   NOT NULL,
    account_id        VARCHAR(16)   NOT NULL,
    book_id           VARCHAR(16)   NOT NULL,
    legal_entity      VARCHAR(48)   NOT NULL,
    currency          VARCHAR(3)    NOT NULL,
    amount            NUMERIC(18,2) NOT NULL,
    business_date     DATE          NOT NULL,
    snapshot_version  VARCHAR(24)   NOT NULL,
    pipeline_run_id   VARCHAR(32)   NOT NULL,
    load_timestamp    TIMESTAMP     NOT NULL,
    snapshot_status   VARCHAR(16)   NOT NULL,   -- 'COMPLETED' | 'FAILED'
    approval_status   VARCHAR(16)   NOT NULL,   -- 'APPROVED'  | 'REJECTED'
    CONSTRAINT pk_dh_fsb_bs PRIMARY KEY (cob_date, position_id)
);

-- ---------------------------------------------------------------------
-- Saturn Report (Tableau)  ->  tableau.report_<name>_<cob>
--   Aggregated FSB regulatory report per (cob, currency), inherited
--   1:1 from whatever the Data Hub snapshot contained.
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS tableau.report_fsb_regulatory;
CREATE TABLE tableau.report_fsb_regulatory (
    report_name       VARCHAR(64)   NOT NULL,
    cob_date          DATE          NOT NULL,
    currency          VARCHAR(3)    NOT NULL,
    position_count    INT           NOT NULL,   -- number of positions in the report line
    total_amount      NUMERIC(20,2) NOT NULL,   -- FSB balance-sheet total for the line
    business_date     DATE          NOT NULL,
    snapshot_version  VARCHAR(24)   NOT NULL,
    pipeline_run_id   VARCHAR(32)   NOT NULL,
    load_timestamp    TIMESTAMP     NOT NULL,
    report_status     VARCHAR(16)   NOT NULL,   -- 'PUBLISHED' (Saturn ran fine)
    CONSTRAINT pk_rpt_fsb_bs PRIMARY KEY (cob_date, currency)
);


-- =====================================================================
--  2. INSERT statements
-- =====================================================================
-- =====================================================================
--  2a. PE Ingestion (staging) — HEALTHY source of truth.
--      300 rows per COB for BOTH 31-Oct and 30-Nov = 600 rows total.
--      Every row ingestion_status = 'SUCCESS'. No gaps, no failures.
--
--      Values are deterministic (derived from the sequence g) so the whole
--      dataset is reproducible and IDENTICAL across the two COBs. That makes
--      the month-over-month comparison exact — the ONLY thing that differs on
--      30-Nov is which rows survive into the snapshot.
-- =====================================================================
INSERT INTO oracle_pe_fsb_staging.fsb_balance_sheet
(feed_name, cob_date, position_id, account_id, book_id, legal_entity, currency, amount,
 business_date, snapshot_version, pipeline_run_id, load_timestamp, ingestion_status)
SELECT
    'FSB_BALANCE_SHEET'                                                 AS feed_name,
    c.cob_date                                                        AS cob_date,
    'POS-' || TO_CHAR(c.cob_date, 'YYYYMMDD') || '-' || LPAD(g::text, 4, '0') AS position_id,
    'ACC-' || LPAD(((g % 40) + 1)::text, 4, '0')                      AS account_id,
    'BK-'  || LPAD(((g % 12) + 1)::text, 3, '0')                      AS book_id,
    (ARRAY['LE-UK-Bank','LE-US-Bank','LE-EU-Holdings','LE-APAC-Ltd',
           'LE-Group-Treasury'])[(g % 5) + 1]                         AS legal_entity,
    (ARRAY['USD','USD','USD','EUR','GBP','JPY'])[(g % 6) + 1]         AS currency,
    ROUND((500000 + ((g * 7919) % 9500000))::numeric, 2)             AS amount,
    c.cob_date                                                       AS business_date,
    'PE-EXTRACT-v1'                                                   AS snapshot_version,
    'PE-RUN-' || TO_CHAR(c.cob_date, 'YYYYMMDD')                      AS pipeline_run_id,
    (c.cob_date + TIME '02:00:00' + (g * INTERVAL '5 seconds'))       AS load_timestamp,
    'SUCCESS'                                                         AS ingestion_status
FROM (VALUES (DATE '2025-10-31'), (DATE '2025-11-30')) AS c(cob_date)
CROSS JOIN generate_series(1, 300) AS g;


-- =====================================================================
--  2b. Treasury Data Hub snapshot — DERIVED from staging.
--
--      31-Oct (healthy): ALL 300 rows written.
--                        snapshot_status = 'COMPLETED', approval = 'APPROVED'.
--
--      30-Nov (INCIDENT): the snapshot pipeline FAILED before completion, so
--                        only the first 210 rows were written (rows whose
--                        sequence > 210 were never flushed). The partial
--                        snapshot is stamped snapshot_status = 'FAILED' and the
--                        completeness gate set approval_status = 'REJECTED'.
--
--      => 90 rows (seq 211..300) exist in staging on 30-Nov but are MISSING
--         from the snapshot. That is the entire root cause.
-- =====================================================================
INSERT INTO dh.snapshot_fsb_balance_sheet
(feed_name, cob_date, position_id, account_id, book_id, legal_entity, currency, amount,
 business_date, snapshot_version, pipeline_run_id, load_timestamp, snapshot_status, approval_status)
SELECT
    s.feed_name,
    s.cob_date,
    s.position_id,
    s.account_id,
    s.book_id,
    s.legal_entity,
    s.currency,
    s.amount,
    s.business_date,
    CASE WHEN s.cob_date = DATE '2025-11-30' THEN 'DH-SNAP-v1-PARTIAL'
         ELSE 'DH-SNAP-v1' END                                       AS snapshot_version,
    'DH-RUN-' || TO_CHAR(s.cob_date, 'YYYYMMDD')                      AS pipeline_run_id,
    (s.cob_date + TIME '03:10:00')                                    AS load_timestamp,
    CASE WHEN s.cob_date = DATE '2025-11-30' THEN 'FAILED'
         ELSE 'COMPLETED' END                                        AS snapshot_status,
    CASE WHEN s.cob_date = DATE '2025-11-30' THEN 'REJECTED'
         ELSE 'APPROVED' END                                         AS approval_status
FROM oracle_pe_fsb_staging.fsb_balance_sheet s
WHERE NOT (
    s.cob_date = DATE '2025-11-30'
    AND CAST(RIGHT(s.position_id, 4) AS INT) > 210   -- 90 rows lost by the failed snapshot pipeline
);


-- =====================================================================
--  2c. Saturn report — DERIVED from the Data Hub snapshot (1:1, no logic).
--
--      Saturn simply aggregates whatever the snapshot contained, per
--      (cob, currency). It ran to completion (report_status = 'PUBLISHED')
--      on BOTH months — Saturn has NO defect. On 30-Nov the report is
--      understated purely because it consumed the incomplete snapshot.
-- =====================================================================
INSERT INTO tableau.report_fsb_regulatory
(report_name, cob_date, currency, position_count, total_amount,
 business_date, snapshot_version, pipeline_run_id, load_timestamp, report_status)
SELECT
    'FSB_Regulatory_Report'                                          AS report_name,
    d.cob_date,
    d.currency,
    COUNT(*)                                                         AS position_count,
    SUM(d.amount)                                                    AS total_amount,
    d.business_date,
    d.snapshot_version,
    'SAT-RUN-' || TO_CHAR(d.cob_date, 'YYYYMMDD')                    AS pipeline_run_id,
    (d.cob_date + TIME '04:05:00')                                   AS load_timestamp,
    'PUBLISHED'                                                      AS report_status
FROM dh.snapshot_fsb_balance_sheet d
GROUP BY d.cob_date, d.currency, d.business_date, d.snapshot_version;


-- =====================================================================
--  3. Compare Saturn report against the Data Hub snapshot.
--
--     STEP 1 of the investigation. The report totals must EXACTLY equal the
--     snapshot aggregates on both months (delta = 0). This proves Saturn is a
--     faithful mirror of the snapshot and has no calculation defect — so the
--     investigation moves DOWN to the Data Hub layer.
-- =====================================================================
WITH snap_agg AS (
    SELECT cob_date, currency, COUNT(*) AS snap_rows, SUM(amount) AS snap_total
    FROM dh.snapshot_fsb_balance_sheet
    GROUP BY cob_date, currency
)
SELECT
    r.cob_date,
    r.currency,
    r.position_count                       AS report_rows,
    s.snap_rows,
    (r.position_count - s.snap_rows)       AS row_delta,        -- expect 0
    r.total_amount                         AS report_total,
    s.snap_total,
    (r.total_amount - s.snap_total)        AS amount_delta      -- expect 0.00
FROM tableau.report_fsb_regulatory r
JOIN snap_agg s
  ON s.cob_date = r.cob_date AND s.currency = r.currency
ORDER BY r.cob_date, r.currency;


-- =====================================================================
--  4. Prove the Data Hub snapshot is INCOMPLETE (vs. healthy staging).
--
--     STEP 2 of the investigation. Staging (PE Ingestion) is complete on both
--     COBs (300 rows). The snapshot matches staging on 31-Oct (300) but is
--     short by 90 on 30-Nov (210) — the missing-row count that exactly
--     explains the Saturn report understatement.
-- =====================================================================
-- 4a. Row-count reconciliation: staging vs snapshot, per COB.
SELECT
    stg.cob_date,
    stg.staging_rows,                                   -- expect 300 both months
    COALESCE(snp.snapshot_rows, 0)            AS snapshot_rows,      -- 300 / 210
    stg.staging_rows - COALESCE(snp.snapshot_rows, 0) AS missing_rows,   -- 0 / 90
    stg.staging_status,                                 -- SUCCESS both months
    COALESCE(snp.snapshot_status, 'NONE')     AS snapshot_status,   -- COMPLETED / FAILED
    COALESCE(snp.approval_status, 'NONE')     AS approval_status    -- APPROVED / REJECTED
FROM (
    SELECT cob_date, COUNT(*) AS staging_rows, MAX(ingestion_status) AS staging_status
    FROM oracle_pe_fsb_staging.fsb_balance_sheet
    GROUP BY cob_date
) stg
LEFT JOIN (
    SELECT cob_date, COUNT(*) AS snapshot_rows,
           MAX(snapshot_status) AS snapshot_status,
           MAX(approval_status) AS approval_status
    FROM dh.snapshot_fsb_balance_sheet
    GROUP BY cob_date
) snp
  ON snp.cob_date = stg.cob_date
ORDER BY stg.cob_date;

-- 4b. The exact 90 rows present in staging but MISSING from the snapshot on
--     30-Nov (anti-join). These are precisely the rows absent from Saturn.
SELECT
    s.cob_date,
    s.position_id,
    s.account_id,
    s.book_id,
    s.legal_entity,
    s.currency,
    s.amount,
    s.ingestion_status                        -- SUCCESS: proven loaded upstream
FROM oracle_pe_fsb_staging.fsb_balance_sheet s
WHERE s.cob_date = DATE '2025-11-30'
  AND NOT EXISTS (
      SELECT 1
      FROM dh.snapshot_fsb_balance_sheet d
      WHERE d.cob_date = s.cob_date
        AND d.position_id = s.position_id
  )
ORDER BY s.position_id;

-- 4c. Magnitude of the gap: balance-sheet amount dropped by the failed snapshot.
SELECT
    'FSB amount lost to incomplete snapshot (COB 2025-11-30)' AS description,
    (SELECT SUM(amount) FROM oracle_pe_fsb_staging.fsb_balance_sheet
      WHERE cob_date = DATE '2025-11-30')                         AS staging_total,
    (SELECT SUM(amount) FROM dh.snapshot_fsb_balance_sheet
      WHERE cob_date = DATE '2025-11-30')                         AS snapshot_total,
    (SELECT SUM(amount) FROM oracle_pe_fsb_staging.fsb_balance_sheet
      WHERE cob_date = DATE '2025-11-30')
      - (SELECT SUM(amount) FROM dh.snapshot_fsb_balance_sheet
          WHERE cob_date = DATE '2025-11-30')                      AS understated_by;


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
    MAX(snapshot_status)  AS snapshot_status,     -- 2025-11-30 => FAILED
    MAX(approval_status)  AS approval_status,     -- 2025-11-30 => REJECTED
    MAX(snapshot_version) AS snapshot_version,    -- 2025-11-30 => *-PARTIAL
    COUNT(*)              AS rows_written
FROM dh.snapshot_fsb_balance_sheet
GROUP BY cob_date
ORDER BY cob_date;

-- 5b. Explicit failed / rejected snapshot rows (the incident COB).
SELECT DISTINCT
    feed_name, cob_date, snapshot_status, approval_status, snapshot_version, pipeline_run_id
FROM dh.snapshot_fsb_balance_sheet
WHERE snapshot_status = 'FAILED'
   OR approval_status = 'REJECTED';

-- 5c. Confirm PE Ingestion is HEALTHY (so we correctly stop and do NOT
--     investigate it): all staging rows for the incident COB are SUCCESS.
SELECT
    cob_date,
    ingestion_status,
    COUNT(*) AS rows
FROM oracle_pe_fsb_staging.fsb_balance_sheet
WHERE cob_date = DATE '2025-11-30'
GROUP BY cob_date, ingestion_status;   -- single row: SUCCESS, 300


-- =====================================================================
--  6. Root-cause summary
-- =====================================================================
--  Root Cause: Treasury Data Hub Monthly Snapshot Pipeline Failure. An
--  incomplete snapshot was published (210 of 300 rows for COB 2025-11-30, with
--  snapshot_status = FAILED and approval_status = REJECTED), which propagated
--  to Saturn reporting and produced an understated / failed FSB report. Since
--  the root cause was identified at Data Hub — and PE Ingestion staging is
--  proven complete and healthy (300 rows, ingestion_status = SUCCESS) — no
--  further investigation into PE Ingestion is required.
--
--  Evidence chain:
--    * Query 3  : Saturn report == Data Hub snapshot (delta 0)  -> Saturn OK.
--    * Query 4a : staging 300 vs snapshot 210 on 30-Nov         -> 90 missing.
--    * Query 4b : the exact 90 missing rows (all SUCCESS in staging).
--    * Query 5a/5b : snapshot_status = FAILED, approval = REJECTED.
--    * Query 5c : PE Ingestion staging fully SUCCESS            -> stop here.
-- =====================================================================
