-- Minimal Snowflake bootstrap for the shared warehouse/database/dbt objects.
-- Both local execution and Snowpark Container Services job execution use these.
-- Adjust identifiers if your account already uses different names.

CREATE WAREHOUSE IF NOT EXISTS DLT_GITHUB_DEMO_WH
  WITH WAREHOUSE_SIZE = 'XSMALL'
       AUTO_SUSPEND = 60
       AUTO_RESUME = TRUE
       INITIALLY_SUSPENDED = TRUE;

CREATE DATABASE IF NOT EXISTS DLT_GITHUB_DEMO;

-- Snowflake dbt project objects expect the curated target schema to exist
-- before compile/execute succeeds.
CREATE SCHEMA IF NOT EXISTS DLT_GITHUB_DEMO.GITHUB_ISSUES_ANALYTICS;

-- dlt creates the target schema/dataset during the first successful run.
-- The executing role needs at least:
--   USAGE ON WAREHOUSE DLT_GITHUB_DEMO_WH
--   USAGE ON DATABASE DLT_GITHUB_DEMO
--   CREATE SCHEMA ON DATABASE DLT_GITHUB_DEMO
