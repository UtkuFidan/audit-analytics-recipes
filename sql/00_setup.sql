-- 00_setup.sql
-- Creates one view per CSV table plus a single-row `params` table holding every threshold the
-- tests use. Paths are relative to the repo root; the Python runner rewrites the `data/` prefix
-- to the data directory you pass on the command line.
--
-- From the DuckDB CLI, in one session: `.read sql/00_setup.sql`, then `.read` each test file.

CREATE OR REPLACE VIEW vendors             AS SELECT * FROM read_csv_auto('data/vendors.csv');
CREATE OR REPLACE VIEW vendor_bank_changes AS SELECT * FROM read_csv_auto('data/vendor_bank_changes.csv');
CREATE OR REPLACE VIEW purchase_orders     AS SELECT * FROM read_csv_auto('data/purchase_orders.csv');
CREATE OR REPLACE VIEW invoices            AS SELECT * FROM read_csv_auto('data/invoices.csv');
CREATE OR REPLACE VIEW payments            AS SELECT * FROM read_csv_auto('data/payments.csv');
CREATE OR REPLACE VIEW gl_journal          AS SELECT * FROM read_csv_auto('data/gl_journal.csv');
CREATE OR REPLACE VIEW employees           AS SELECT * FROM read_csv_auto('data/employees.csv');
CREATE OR REPLACE VIEW user_accounts       AS SELECT * FROM read_csv_auto('data/user_accounts.csv');
CREATE OR REPLACE VIEW user_roles          AS SELECT * FROM read_csv_auto('data/user_roles.csv');
CREATE OR REPLACE VIEW roles               AS SELECT * FROM read_csv_auto('data/roles.csv');
CREATE OR REPLACE VIEW role_permissions    AS SELECT * FROM read_csv_auto('data/role_permissions.csv');
CREATE OR REPLACE VIEW sod_matrix          AS SELECT * FROM read_csv_auto('data/sod_matrix.csv');
CREATE OR REPLACE VIEW holidays            AS SELECT * FROM read_csv_auto('data/holidays.csv');

CREATE OR REPLACE TABLE params AS SELECT
    DATE '2025-12-31' AS as_of,               -- audit cut-off date
    10000             AS approval_limit,      -- PO approval limit
    0.70              AS split_floor_ratio,   -- split POs must each be >= this share of the limit
    7                 AS split_window_days,   -- ...and fall within this many days of each other
    14                AS bank_window_days,    -- payment within N days after a bank-detail change
    5000              AS round_min_amount,    -- ignore round journals below this
    1000              AS round_modulus,       -- "round" means a multiple of this
    7                 AS fuzzy_date_days,     -- fuzzy duplicate: invoice dates within N days
    0.92              AS fuzzy_name_similarity, -- Jaro-Winkler on normalised vendor names
    90                AS dormant_days;        -- privileged account idle longer than N days
