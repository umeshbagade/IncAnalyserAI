-- =====================================================================
--  Mock data for incident: DRVC_MTM_DATA_SPIKE_FOR_TENOR_D60_61
--  Feed        : MTM_VOL_STRESS  (MTM Volatility Stress Cash Flows)
--  COB dates   : 2025-07-02 (2-Jul)  and  2025-07-03 (3-Jul)
--
--  Pipeline (data flows top -> bottom, RCA investigates bottom -> top):
--
--      Upload Ingestion (Hive)   hive.ingest_mtm_vol_stress
--              |                  (raw source transactions)
--              v
--      Data Hub Snapshot         dh.snapshot_mtm_vol_stress
--              |                  (cumulative tenor curve, inherited)
--              v
--      Saturn Reporting          tableau.report_mtm_vol_stress
--                                 (cumulative tenor curve, inherited)
--
--  Root cause:
--    A source-side difference between 2-Jul and 3-Jul introduced ONE
--    additional D60 transaction during Upload Ingestion. That single row
--    propagates unchanged through Data Hub and Saturn, so only the D60
--    tenor increment differs between the two days.
--
--  Design guarantee:
--    Only the Upload Ingestion (source) rows are inserted by hand. The
--    Data Hub and Saturn cumulative curves are DERIVED from ingestion via
--    a cumulative window SUM, so there are provably no transformations
--    between layers and every increment except D60 is identical.
--
--  Dialect: PostgreSQL-compatible (recursive CTE + window functions).
--           Notes inline for the Hive/Spark equivalent.
-- =====================================================================


-- =====================================================================
--  1. CREATE TABLE statements
-- =====================================================================

CREATE SCHEMA IF NOT EXISTS hive;      -- maps to Hive database `hive`, schema `ingest`
CREATE SCHEMA IF NOT EXISTS dh;        -- Data Hub
CREATE SCHEMA IF NOT EXISTS tableau;   -- Saturn reporting (Tableau extract)

-- ---------------------------------------------------------------------
-- Upload Ingestion (Hive)  ->  hive.ingest.<feed>_<cob>
--   In production this is partitioned by `cob`; the mock table keeps a
--   `cob` column to represent the partition key.
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS hive.ingest_mtm_vol_stress;
CREATE TABLE hive.ingest_mtm_vol_stress (
    trade_id             VARCHAR(32)   NOT NULL,
    feed                 VARCHAR(32)   NOT NULL,
    cob                  DATE          NOT NULL,   -- partition key (Change-of-Business date)
    currency             VARCHAR(3)    NOT NULL,
    amount               NUMERIC(18,2) NOT NULL,   -- per-transaction contribution to its tenor bucket
    tenor_seq            INT           NOT NULL,    -- 1..60  (D1..D60)
    tenor_label          VARCHAR(4)    NOT NULL,    -- 'D1'..'D60'
    source_book_id       VARCHAR(16)   NOT NULL,    -- contributor attribute
    db_party_d_party_id  VARCHAR(16)   NOT NULL,    -- contributor attribute
    paragon_org_id       VARCHAR(16)   NOT NULL,    -- contributor attribute
    d_ubr_id             VARCHAR(16)   NOT NULL,    -- contributor attribute
    snapshot_date        DATE          NOT NULL,
    pipeline_run_id      VARCHAR(32)   NOT NULL,
    status               VARCHAR(16)   NOT NULL,    -- 'INGESTED'
    CONSTRAINT pk_ingest_mtm PRIMARY KEY (trade_id)
);

-- ---------------------------------------------------------------------
-- Data Hub Snapshot  ->  dh.snapshot_<feed>_<cob>
--   Stores the CUMULATIVE tenor curve (D1..D60) per cob.
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS dh.snapshot_mtm_vol_stress;
CREATE TABLE dh.snapshot_mtm_vol_stress (
    feed                 VARCHAR(32)   NOT NULL,
    cob                  DATE          NOT NULL,
    tenor_seq            INT           NOT NULL,    -- 1..60
    tenor_label          VARCHAR(4)    NOT NULL,    -- 'D1'..'D60'
    cumulative_amount    NUMERIC(18,2) NOT NULL,    -- running sum of ingestion increments D1..Dn
    currency             VARCHAR(3)    NOT NULL,
    snapshot_date        DATE          NOT NULL,
    pipeline_run_id      VARCHAR(32)   NOT NULL,
    status               VARCHAR(16)   NOT NULL,    -- 'LOADED'
    CONSTRAINT pk_dh_snapshot_mtm PRIMARY KEY (cob, tenor_seq)
);

-- ---------------------------------------------------------------------
-- Saturn Reporting  ->  tableau.report_<name>_<cob>
--   Same cumulative tenor curve, inherited 1:1 from Data Hub.
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS tableau.report_mtm_vol_stress;
CREATE TABLE tableau.report_mtm_vol_stress (
    report_name          VARCHAR(64)   NOT NULL,
    cob                  DATE          NOT NULL,
    tenor_seq            INT           NOT NULL,    -- 1..60
    tenor_label          VARCHAR(4)    NOT NULL,    -- 'D1'..'D60'
    cumulative_amount    NUMERIC(18,2) NOT NULL,
    currency             VARCHAR(3)    NOT NULL,
    snapshot_date        DATE          NOT NULL,
    pipeline_run_id      VARCHAR(32)   NOT NULL,
    status               VARCHAR(16)   NOT NULL,    -- 'PUBLISHED'
    CONSTRAINT pk_tableau_report_mtm PRIMARY KEY (cob, tenor_seq)
);


-- =====================================================================
--  2. INSERT statements — Upload Ingestion source transactions
--
--  The 27 "base" transactions are IDENTICAL across both COBs on every
--  business-key column (tenor_seq, amount, source_book_id,
--  db_party_d_party_id, paragon_org_id, d_ubr_id). Only trade_id,
--  snapshot_date and pipeline_run_id differ per day.
--
--  => Every per-tenor bucket sum matches between 2-Jul and 3-Jul,
--     therefore every increment D1..D59 is identical.
--
--  2-Jul additionally contains ONE extra D60 transaction
--  (trade TRD-20250702-028) that has NO counterpart on 3-Jul.
--  => D60 is the only tenor whose increment differs.
-- =====================================================================

-- ---------------------- COB = 2025-07-02 (2-Jul) ---------------------
INSERT INTO hive.ingest_mtm_vol_stress
(trade_id, feed, cob, currency, amount, tenor_seq, tenor_label,
 source_book_id, db_party_d_party_id, paragon_org_id, d_ubr_id,
 snapshot_date, pipeline_run_id, status) VALUES
('TRD-20250702-001','MTM_VOL_STRESS',DATE '2025-07-02','USD',125000.00, 1,'D1', 'BK-1001','DP-2001','ORG-3001','UBR-4001',DATE '2025-07-02','ING-RUN-20250702','INGESTED'),
('TRD-20250702-002','MTM_VOL_STRESS',DATE '2025-07-02','USD', 98000.00, 2,'D2', 'BK-1002','DP-2002','ORG-3002','UBR-4002',DATE '2025-07-02','ING-RUN-20250702','INGESTED'),
('TRD-20250702-003','MTM_VOL_STRESS',DATE '2025-07-02','USD',143500.00, 3,'D3', 'BK-1003','DP-2003','ORG-3001','UBR-4003',DATE '2025-07-02','ING-RUN-20250702','INGESTED'),
('TRD-20250702-004','MTM_VOL_STRESS',DATE '2025-07-02','USD', 76500.00, 5,'D5', 'BK-1004','DP-2004','ORG-3003','UBR-4004',DATE '2025-07-02','ING-RUN-20250702','INGESTED'),
('TRD-20250702-005','MTM_VOL_STRESS',DATE '2025-07-02','USD',112000.00, 7,'D7', 'BK-1005','DP-2001','ORG-3002','UBR-4005',DATE '2025-07-02','ING-RUN-20250702','INGESTED'),
('TRD-20250702-006','MTM_VOL_STRESS',DATE '2025-07-02','USD', 88000.00,10,'D10','BK-1006','DP-2005','ORG-3004','UBR-4006',DATE '2025-07-02','ING-RUN-20250702','INGESTED'),
('TRD-20250702-007','MTM_VOL_STRESS',DATE '2025-07-02','USD',156000.00,12,'D12','BK-1007','DP-2006','ORG-3001','UBR-4007',DATE '2025-07-02','ING-RUN-20250702','INGESTED'),
('TRD-20250702-008','MTM_VOL_STRESS',DATE '2025-07-02','USD', 67000.00,15,'D15','BK-1008','DP-2002','ORG-3005','UBR-4008',DATE '2025-07-02','ING-RUN-20250702','INGESTED'),
('TRD-20250702-009','MTM_VOL_STRESS',DATE '2025-07-02','USD',134500.00,18,'D18','BK-1009','DP-2007','ORG-3003','UBR-4009',DATE '2025-07-02','ING-RUN-20250702','INGESTED'),
('TRD-20250702-010','MTM_VOL_STRESS',DATE '2025-07-02','USD',102000.00,20,'D20','BK-1010','DP-2003','ORG-3002','UBR-4010',DATE '2025-07-02','ING-RUN-20250702','INGESTED'),
('TRD-20250702-011','MTM_VOL_STRESS',DATE '2025-07-02','USD', 91500.00,24,'D24','BK-1011','DP-2008','ORG-3006','UBR-4011',DATE '2025-07-02','ING-RUN-20250702','INGESTED'),
('TRD-20250702-012','MTM_VOL_STRESS',DATE '2025-07-02','USD',118000.00,28,'D28','BK-1012','DP-2004','ORG-3001','UBR-4012',DATE '2025-07-02','ING-RUN-20250702','INGESTED'),
('TRD-20250702-013','MTM_VOL_STRESS',DATE '2025-07-02','USD',145000.00,30,'D30','BK-1013','DP-2009','ORG-3004','UBR-4013',DATE '2025-07-02','ING-RUN-20250702','INGESTED'),
('TRD-20250702-014','MTM_VOL_STRESS',DATE '2025-07-02','USD', 73500.00,33,'D33','BK-1014','DP-2005','ORG-3007','UBR-4014',DATE '2025-07-02','ING-RUN-20250702','INGESTED'),
('TRD-20250702-015','MTM_VOL_STRESS',DATE '2025-07-02','USD',129000.00,36,'D36','BK-1015','DP-2010','ORG-3002','UBR-4015',DATE '2025-07-02','ING-RUN-20250702','INGESTED'),
('TRD-20250702-016','MTM_VOL_STRESS',DATE '2025-07-02','USD', 84000.00,40,'D40','BK-1016','DP-2006','ORG-3005','UBR-4016',DATE '2025-07-02','ING-RUN-20250702','INGESTED'),
('TRD-20250702-017','MTM_VOL_STRESS',DATE '2025-07-02','USD',137500.00,42,'D42','BK-1017','DP-2011','ORG-3003','UBR-4017',DATE '2025-07-02','ING-RUN-20250702','INGESTED'),
('TRD-20250702-018','MTM_VOL_STRESS',DATE '2025-07-02','USD', 96000.00,45,'D45','BK-1018','DP-2007','ORG-3001','UBR-4018',DATE '2025-07-02','ING-RUN-20250702','INGESTED'),
('TRD-20250702-019','MTM_VOL_STRESS',DATE '2025-07-02','USD',121500.00,48,'D48','BK-1019','DP-2012','ORG-3006','UBR-4019',DATE '2025-07-02','ING-RUN-20250702','INGESTED'),
('TRD-20250702-020','MTM_VOL_STRESS',DATE '2025-07-02','USD',108000.00,50,'D50','BK-1020','DP-2008','ORG-3004','UBR-4020',DATE '2025-07-02','ING-RUN-20250702','INGESTED'),
('TRD-20250702-021','MTM_VOL_STRESS',DATE '2025-07-02','USD',152000.00,52,'D52','BK-1021','DP-2013','ORG-3002','UBR-4021',DATE '2025-07-02','ING-RUN-20250702','INGESTED'),
('TRD-20250702-022','MTM_VOL_STRESS',DATE '2025-07-02','USD', 79500.00,54,'D54','BK-1022','DP-2009','ORG-3007','UBR-4022',DATE '2025-07-02','ING-RUN-20250702','INGESTED'),
('TRD-20250702-023','MTM_VOL_STRESS',DATE '2025-07-02','USD',141000.00,56,'D56','BK-1023','DP-2014','ORG-3003','UBR-4023',DATE '2025-07-02','ING-RUN-20250702','INGESTED'),
('TRD-20250702-024','MTM_VOL_STRESS',DATE '2025-07-02','USD', 93000.00,58,'D58','BK-1024','DP-2010','ORG-3005','UBR-4024',DATE '2025-07-02','ING-RUN-20250702','INGESTED'),
('TRD-20250702-025','MTM_VOL_STRESS',DATE '2025-07-02','USD',116500.00,59,'D59','BK-1025','DP-2015','ORG-3001','UBR-4025',DATE '2025-07-02','ING-RUN-20250702','INGESTED'),
('TRD-20250702-026','MTM_VOL_STRESS',DATE '2025-07-02','USD',132000.00,60,'D60','BK-1026','DP-2011','ORG-3004','UBR-4026',DATE '2025-07-02','ING-RUN-20250702','INGESTED'),
('TRD-20250702-027','MTM_VOL_STRESS',DATE '2025-07-02','USD', 87500.00,60,'D60','BK-1027','DP-2012','ORG-3006','UBR-4027',DATE '2025-07-02','ING-RUN-20250702','INGESTED'),
-- >>> THE ADDITIONAL D60 SOURCE TRANSACTION (root cause) — present ONLY on 2-Jul <<<
('TRD-20250702-028','MTM_VOL_STRESS',DATE '2025-07-02','USD', 74250.00,60,'D60','BK-9907','DP-2099','ORG-3099','UBR-4471',DATE '2025-07-02','ING-RUN-20250702','INGESTED');

-- ---------------------- COB = 2025-07-03 (3-Jul) ---------------------
--  Identical 27 base transactions, NO extra D60 row.
INSERT INTO hive.ingest_mtm_vol_stress
(trade_id, feed, cob, currency, amount, tenor_seq, tenor_label,
 source_book_id, db_party_d_party_id, paragon_org_id, d_ubr_id,
 snapshot_date, pipeline_run_id, status) VALUES
('TRD-20250703-001','MTM_VOL_STRESS',DATE '2025-07-03','USD',125000.00, 1,'D1', 'BK-1001','DP-2001','ORG-3001','UBR-4001',DATE '2025-07-03','ING-RUN-20250703','INGESTED'),
('TRD-20250703-002','MTM_VOL_STRESS',DATE '2025-07-03','USD', 98000.00, 2,'D2', 'BK-1002','DP-2002','ORG-3002','UBR-4002',DATE '2025-07-03','ING-RUN-20250703','INGESTED'),
('TRD-20250703-003','MTM_VOL_STRESS',DATE '2025-07-03','USD',143500.00, 3,'D3', 'BK-1003','DP-2003','ORG-3001','UBR-4003',DATE '2025-07-03','ING-RUN-20250703','INGESTED'),
('TRD-20250703-004','MTM_VOL_STRESS',DATE '2025-07-03','USD', 76500.00, 5,'D5', 'BK-1004','DP-2004','ORG-3003','UBR-4004',DATE '2025-07-03','ING-RUN-20250703','INGESTED'),
('TRD-20250703-005','MTM_VOL_STRESS',DATE '2025-07-03','USD',112000.00, 7,'D7', 'BK-1005','DP-2001','ORG-3002','UBR-4005',DATE '2025-07-03','ING-RUN-20250703','INGESTED'),
('TRD-20250703-006','MTM_VOL_STRESS',DATE '2025-07-03','USD', 88000.00,10,'D10','BK-1006','DP-2005','ORG-3004','UBR-4006',DATE '2025-07-03','ING-RUN-20250703','INGESTED'),
('TRD-20250703-007','MTM_VOL_STRESS',DATE '2025-07-03','USD',156000.00,12,'D12','BK-1007','DP-2006','ORG-3001','UBR-4007',DATE '2025-07-03','ING-RUN-20250703','INGESTED'),
('TRD-20250703-008','MTM_VOL_STRESS',DATE '2025-07-03','USD', 67000.00,15,'D15','BK-1008','DP-2002','ORG-3005','UBR-4008',DATE '2025-07-03','ING-RUN-20250703','INGESTED'),
('TRD-20250703-009','MTM_VOL_STRESS',DATE '2025-07-03','USD',134500.00,18,'D18','BK-1009','DP-2007','ORG-3003','UBR-4009',DATE '2025-07-03','ING-RUN-20250703','INGESTED'),
('TRD-20250703-010','MTM_VOL_STRESS',DATE '2025-07-03','USD',102000.00,20,'D20','BK-1010','DP-2003','ORG-3002','UBR-4010',DATE '2025-07-03','ING-RUN-20250703','INGESTED'),
('TRD-20250703-011','MTM_VOL_STRESS',DATE '2025-07-03','USD', 91500.00,24,'D24','BK-1011','DP-2008','ORG-3006','UBR-4011',DATE '2025-07-03','ING-RUN-20250703','INGESTED'),
('TRD-20250703-012','MTM_VOL_STRESS',DATE '2025-07-03','USD',118000.00,28,'D28','BK-1012','DP-2004','ORG-3001','UBR-4012',DATE '2025-07-03','ING-RUN-20250703','INGESTED'),
('TRD-20250703-013','MTM_VOL_STRESS',DATE '2025-07-03','USD',145000.00,30,'D30','BK-1013','DP-2009','ORG-3004','UBR-4013',DATE '2025-07-03','ING-RUN-20250703','INGESTED'),
('TRD-20250703-014','MTM_VOL_STRESS',DATE '2025-07-03','USD', 73500.00,33,'D33','BK-1014','DP-2005','ORG-3007','UBR-4014',DATE '2025-07-03','ING-RUN-20250703','INGESTED'),
('TRD-20250703-015','MTM_VOL_STRESS',DATE '2025-07-03','USD',129000.00,36,'D36','BK-1015','DP-2010','ORG-3002','UBR-4015',DATE '2025-07-03','ING-RUN-20250703','INGESTED'),
('TRD-20250703-016','MTM_VOL_STRESS',DATE '2025-07-03','USD', 84000.00,40,'D40','BK-1016','DP-2006','ORG-3005','UBR-4016',DATE '2025-07-03','ING-RUN-20250703','INGESTED'),
('TRD-20250703-017','MTM_VOL_STRESS',DATE '2025-07-03','USD',137500.00,42,'D42','BK-1017','DP-2011','ORG-3003','UBR-4017',DATE '2025-07-03','ING-RUN-20250703','INGESTED'),
('TRD-20250703-018','MTM_VOL_STRESS',DATE '2025-07-03','USD', 96000.00,45,'D45','BK-1018','DP-2007','ORG-3001','UBR-4018',DATE '2025-07-03','ING-RUN-20250703','INGESTED'),
('TRD-20250703-019','MTM_VOL_STRESS',DATE '2025-07-03','USD',121500.00,48,'D48','BK-1019','DP-2012','ORG-3006','UBR-4019',DATE '2025-07-03','ING-RUN-20250703','INGESTED'),
('TRD-20250703-020','MTM_VOL_STRESS',DATE '2025-07-03','USD',108000.00,50,'D50','BK-1020','DP-2008','ORG-3004','UBR-4020',DATE '2025-07-03','ING-RUN-20250703','INGESTED'),
('TRD-20250703-021','MTM_VOL_STRESS',DATE '2025-07-03','USD',152000.00,52,'D52','BK-1021','DP-2013','ORG-3002','UBR-4021',DATE '2025-07-03','ING-RUN-20250703','INGESTED'),
('TRD-20250703-022','MTM_VOL_STRESS',DATE '2025-07-03','USD', 79500.00,54,'D54','BK-1022','DP-2009','ORG-3007','UBR-4022',DATE '2025-07-03','ING-RUN-20250703','INGESTED'),
('TRD-20250703-023','MTM_VOL_STRESS',DATE '2025-07-03','USD',141000.00,56,'D56','BK-1023','DP-2014','ORG-3003','UBR-4023',DATE '2025-07-03','ING-RUN-20250703','INGESTED'),
('TRD-20250703-024','MTM_VOL_STRESS',DATE '2025-07-03','USD', 93000.00,58,'D58','BK-1024','DP-2010','ORG-3005','UBR-4024',DATE '2025-07-03','ING-RUN-20250703','INGESTED'),
('TRD-20250703-025','MTM_VOL_STRESS',DATE '2025-07-03','USD',116500.00,59,'D59','BK-1025','DP-2015','ORG-3001','UBR-4025',DATE '2025-07-03','ING-RUN-20250703','INGESTED'),
('TRD-20250703-026','MTM_VOL_STRESS',DATE '2025-07-03','USD',132000.00,60,'D60','BK-1026','DP-2011','ORG-3004','UBR-4026',DATE '2025-07-03','ING-RUN-20250703','INGESTED'),
('TRD-20250703-027','MTM_VOL_STRESS',DATE '2025-07-03','USD', 87500.00,60,'D60','BK-1027','DP-2012','ORG-3006','UBR-4027',DATE '2025-07-03','ING-RUN-20250703','INGESTED');


-- =====================================================================
--  Derive Data Hub from Upload Ingestion (cumulative tenor curve).
--
--  Data Hub inherits EXACTLY the ingestion values: the per-tenor
--  increment = SUM(amount) of source rows at that tenor, and the stored
--  cumulative_amount = running total of those increments across D1..D60.
--  A tenor spine (1..60) is used so every tenor has a row even when no
--  source transaction fell on it (increment 0, cumulative flat).
--
--  Hive/Spark note: replace the recursive CTE with
--      SELECT posexplode(sequence(1,60)) AS (pos, tenor_seq)
--  or a small numbers table.
-- =====================================================================
INSERT INTO dh.snapshot_mtm_vol_stress
(feed, cob, tenor_seq, tenor_label, cumulative_amount, currency,
 snapshot_date, pipeline_run_id, status)
WITH RECURSIVE tenor_spine(tenor_seq) AS (
    SELECT 1
    UNION ALL
    SELECT tenor_seq + 1 FROM tenor_spine WHERE tenor_seq < 60
),
cob_list(cob) AS (
    VALUES (DATE '2025-07-02'), (DATE '2025-07-03')
),
increments AS (
    SELECT c.cob,
           s.tenor_seq,
           COALESCE(SUM(i.amount), 0) AS increment_amount
    FROM cob_list c
    CROSS JOIN tenor_spine s
    LEFT JOIN hive.ingest_mtm_vol_stress i
           ON i.cob = c.cob
          AND i.tenor_seq = s.tenor_seq
    GROUP BY c.cob, s.tenor_seq
)
SELECT
    'MTM_VOL_STRESS'                                   AS feed,
    cob,
    tenor_seq,
    'D' || tenor_seq                                   AS tenor_label,
    SUM(increment_amount) OVER (
        PARTITION BY cob ORDER BY tenor_seq
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )                                                  AS cumulative_amount,
    'USD'                                              AS currency,
    cob                                                AS snapshot_date,
    'DH-RUN-' || TO_CHAR(cob, 'YYYYMMDD')              AS pipeline_run_id,
    'LOADED'                                           AS status
FROM increments;


-- =====================================================================
--  Derive Saturn from Data Hub (pure 1:1 inheritance, no transformation).
-- =====================================================================
INSERT INTO tableau.report_mtm_vol_stress
(report_name, cob, tenor_seq, tenor_label, cumulative_amount, currency,
 snapshot_date, pipeline_run_id, status)
SELECT
    'MTM_Volatility_Stress_Cash_Flows'    AS report_name,
    cob,
    tenor_seq,
    tenor_label,
    cumulative_amount,
    currency,
    snapshot_date,
    'SAT-RUN-' || TO_CHAR(cob, 'YYYYMMDD') AS pipeline_run_id,
    'PUBLISHED'                            AS status
FROM dh.snapshot_mtm_vol_stress;


-- =====================================================================
--  3. Calculate incremental tenor values  (Increment(Dn) = Dn - D(n-1))
--     Run against Saturn (Step 1), Data Hub (Step 2) — same shape.
-- =====================================================================
-- Saturn increments:
SELECT
    cob,
    tenor_label,
    cumulative_amount,
    cumulative_amount
        - COALESCE(LAG(cumulative_amount) OVER (PARTITION BY cob ORDER BY tenor_seq), 0)
        AS increment_amount
FROM tableau.report_mtm_vol_stress
ORDER BY cob, tenor_seq;

-- Data Hub increments (identical query, different table):
SELECT
    cob,
    tenor_label,
    cumulative_amount,
    cumulative_amount
        - COALESCE(LAG(cumulative_amount) OVER (PARTITION BY cob ORDER BY tenor_seq), 0)
        AS increment_amount
FROM dh.snapshot_mtm_vol_stress
ORDER BY cob, tenor_seq;


-- =====================================================================
--  4. Identify the FIRST mismatching tenor between 2-Jul and 3-Jul.
--     Expected result: exactly one row -> D60.
-- =====================================================================
WITH incr AS (
    SELECT
        cob,
        tenor_seq,
        tenor_label,
        cumulative_amount
            - COALESCE(LAG(cumulative_amount) OVER (PARTITION BY cob ORDER BY tenor_seq), 0)
            AS increment_amount
    FROM tableau.report_mtm_vol_stress
)
SELECT
    d2.tenor_seq,
    d2.tenor_label,
    d2.increment_amount                          AS increment_02jul,
    d3.increment_amount                          AS increment_03jul,
    (d2.increment_amount - d3.increment_amount)  AS increment_diff
FROM incr d2
JOIN incr d3
      ON d2.tenor_seq = d3.tenor_seq
WHERE d2.cob = DATE '2025-07-02'
  AND d3.cob = DATE '2025-07-03'
  AND d2.increment_amount <> d3.increment_amount
ORDER BY d2.tenor_seq
LIMIT 1;   -- FIRST failing tenor => D60 (diff = 74,250.00)


-- =====================================================================
--  5. Drill-down queries (the RCA path: Saturn -> Data Hub -> Ingestion)
-- =====================================================================

-- 5a. SATURN drill-down — confirm D60 is the first tenor whose increment
--     differs. Focus on the D58..D60 window for clarity.
WITH incr AS (
    SELECT cob, tenor_seq, tenor_label,
           cumulative_amount
             - COALESCE(LAG(cumulative_amount) OVER (PARTITION BY cob ORDER BY tenor_seq), 0)
             AS increment_amount,
           cumulative_amount
    FROM tableau.report_mtm_vol_stress
)
SELECT tenor_label,
       MAX(CASE WHEN cob = DATE '2025-07-02' THEN increment_amount END) AS incr_02jul,
       MAX(CASE WHEN cob = DATE '2025-07-03' THEN increment_amount END) AS incr_03jul,
       MAX(CASE WHEN cob = DATE '2025-07-02' THEN cumulative_amount END) AS cum_02jul,
       MAX(CASE WHEN cob = DATE '2025-07-03' THEN cumulative_amount END) AS cum_03jul
FROM incr
WHERE tenor_seq BETWEEN 58 AND 60
GROUP BY tenor_seq, tenor_label
ORDER BY tenor_seq;

-- 5b. DATA HUB drill-down — validate the SAME D60 discrepancy exists one
--     layer down (proves Saturn faithfully inherited it).
WITH incr AS (
    SELECT cob, tenor_seq, tenor_label,
           cumulative_amount
             - COALESCE(LAG(cumulative_amount) OVER (PARTITION BY cob ORDER BY tenor_seq), 0)
             AS increment_amount
    FROM dh.snapshot_mtm_vol_stress
)
SELECT tenor_label,
       MAX(CASE WHEN cob = DATE '2025-07-02' THEN increment_amount END) AS incr_02jul,
       MAX(CASE WHEN cob = DATE '2025-07-03' THEN increment_amount END) AS incr_03jul,
       MAX(CASE WHEN cob = DATE '2025-07-02' THEN increment_amount END)
         - MAX(CASE WHEN cob = DATE '2025-07-03' THEN increment_amount END) AS incr_diff
FROM incr
WHERE tenor_seq = 60
GROUP BY tenor_seq, tenor_label;

-- 5c. UPLOAD INGESTION drill-down — compare the actual source records that
--     make up the D60 bucket on each day.
SELECT cob, trade_id, amount,
       source_book_id, db_party_d_party_id, paragon_org_id, d_ubr_id, status
FROM hive.ingest_mtm_vol_stress
WHERE tenor_seq = 60
ORDER BY cob, trade_id;

-- 5d. UPLOAD INGESTION root-cause pinpoint — the exact extra transaction:
--     present on 2-Jul, with NO matching source row on 3-Jul (matched on
--     the contributor business key). Returns exactly ONE row.
SELECT i2.cob, i2.trade_id, i2.tenor_label, i2.amount, i2.currency,
       i2.source_book_id, i2.db_party_d_party_id, i2.paragon_org_id, i2.d_ubr_id,
       i2.pipeline_run_id, i2.status
FROM hive.ingest_mtm_vol_stress i2
WHERE i2.cob = DATE '2025-07-02'
  AND i2.tenor_seq = 60
  AND NOT EXISTS (
      SELECT 1
      FROM hive.ingest_mtm_vol_stress i3
      WHERE i3.cob = DATE '2025-07-03'
        AND i3.tenor_seq          = i2.tenor_seq
        AND i3.amount             = i2.amount
        AND i3.source_book_id     = i2.source_book_id
        AND i3.db_party_d_party_id = i2.db_party_d_party_id
        AND i3.paragon_org_id     = i2.paragon_org_id
        AND i3.d_ubr_id           = i2.d_ubr_id
  );

-- 5e. (Optional) Bucket-level confirmation of the gap magnitude at D60.
SELECT tenor_label,
       SUM(CASE WHEN cob = DATE '2025-07-02' THEN amount ELSE 0 END) AS d60_total_02jul,
       SUM(CASE WHEN cob = DATE '2025-07-03' THEN amount ELSE 0 END) AS d60_total_03jul,
       SUM(CASE WHEN cob = DATE '2025-07-02' THEN amount ELSE 0 END)
         - SUM(CASE WHEN cob = DATE '2025-07-03' THEN amount ELSE 0 END) AS gap
FROM hive.ingest_mtm_vol_stress
WHERE tenor_seq = 60
GROUP BY tenor_label;


-- =====================================================================
--  6. Root-cause explanation
-- =====================================================================
--  The investigation starts at SATURN and compares cumulative-to-increment
--  tenor values for 2-Jul vs 3-Jul. Increments D1..D59 are identical; the
--  first (and only) mismatching tenor is D60:
--
--      D60 increment 3-Jul = 132,000.00 + 87,500.00              = 219,500.00
--      D60 increment 2-Jul = 132,000.00 + 87,500.00 + 74,250.00  = 293,750.00
--      Difference                                                =  74,250.00
--
--  The same D60 discrepancy is confirmed in DATA HUB (query 5b), proving the
--  reporting layers are faithful and the problem originates upstream.
--
--  Drilling into UPLOAD INGESTION (query 5d) isolates the exact source
--  transaction responsible:
--
--      trade_id            : TRD-20250702-028
--      cob                 : 2025-07-02  (present on 2-Jul, ABSENT on 3-Jul)
--      tenor               : D60
--      amount              : 74,250.00 USD
--      source_book_id      : BK-9907
--      db_party_d_party_id : DP-2099
--      paragon_org_id      : ORG-3099
--      d_ubr_id            : UBR-4471
--
--  ROOT CAUSE: A source-side difference between 2-Jul and 3-Jul introduced
--  this one additional D60 transaction (book BK-9907 / UBR-4471) during
--  Upload Ingestion. It propagated unchanged through Data Hub and Saturn,
--  inflating the D60 cumulative tenor value by exactly 74,250.00 on 2-Jul.
--  Remediation: reconcile source book BK-9907 with the upstream provider
--  extract for 2-Jul and re-run the ingestion pipeline.
-- =====================================================================
