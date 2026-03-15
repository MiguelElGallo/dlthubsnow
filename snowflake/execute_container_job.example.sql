-- Replace the image placeholder before executing.
-- No Snowflake connection secret is needed inside SPCS; dlt uses Snowflake's
-- auto-mounted OAuth token when `authenticator = oauth`.
-- Upload snowflake/github_issues_job.yaml to @DLT_GITHUB_DEMO.PUBLIC.DLT_GITHUB_CONTAINER_STAGE first.

USE DATABASE DLT_GITHUB_DEMO;
USE SCHEMA PUBLIC;

DROP SERVICE IF EXISTS GITHUB_ISSUES_LOAD_JOB FORCE;

EXECUTE JOB SERVICE
  IN COMPUTE POOL DLT_GITHUB_DEMO_POOL
  NAME = GITHUB_ISSUES_LOAD_JOB
  ASYNC = TRUE
  QUERY_WAREHOUSE = DLT_GITHUB_DEMO_WH
  EXTERNAL_ACCESS_INTEGRATIONS = (DLT_GITHUB_GH_EAI)
  FROM @DLT_GITHUB_CONTAINER_STAGE
  SPECIFICATION_TEMPLATE_FILE = 'github_issues_job.yaml'
  USING (
    image_url => 'REPLACE_WITH_IMAGE_URL',
    github_owner => 'dlt-hub',
    github_repo => 'dlt',
    github_state => 'all',
    dataset_name => 'github_issues_demo',
    pipeline_name => 'dlthubsnow',
    full_refresh => 'false',
    snowflake_database => 'DLT_GITHUB_DEMO',
    snowflake_warehouse => 'DLT_GITHUB_DEMO_WH'
  );

CALL GITHUB_ISSUES_LOAD_JOB!SPCS_WAIT_FOR('DONE', 900);

DESCRIBE SERVICE GITHUB_ISSUES_LOAD_JOB;
