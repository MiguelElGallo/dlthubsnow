-- Replace database/schema names below if you chose different values.
-- Use this after either a local dlt run or a Snowpark Container Services job run.
USE DATABASE DLT_GITHUB_DEMO;
USE SCHEMA GITHUB_ISSUES_DEMO;

SHOW TABLES;

SELECT COUNT(*) AS issue_rows,
       MIN(updated_at) AS oldest_issue_update,
       MAX(updated_at) AS newest_issue_update
FROM github_issues;

SELECT id, number, state, title, updated_at
FROM github_issues
ORDER BY updated_at DESC
LIMIT 20;

SELECT load_id, status, inserted_at, schema_name
FROM _dlt_loads
ORDER BY inserted_at DESC
LIMIT 10;

SELECT version_hash, pipeline_name, created_at
FROM _dlt_pipeline_state
ORDER BY created_at DESC
LIMIT 10;
