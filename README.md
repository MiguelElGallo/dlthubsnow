# dlthubsnow

Small, reviewable demo for running a `dlt` GitHub Issues pipeline **inside Snowflake** with **Snowpark Container Services**, then transforming the landed raw table with a minimal **dbt** layer executed through Snowflake-native dbt Projects.

## Supported runtime model

This repo supports **one** runtime path for the `dlt` load:

- **Snowpark Container Services job service**

The Python package is still developed and validated locally with `uv`, but the demo runtime is the Snowflake container job, not `uv run dlthubsnow`.

## End-to-end flow

```text
GitHub Issues API
  -> container image built from this repo
  -> Snowpark Container Services job service
  -> dlt pipeline/resource (incremental on updated_at, merge key id)
  -> Snowflake raw table: <DB>.<DLT_DATASET>.github_issues
  -> dbt source: github_raw.github_issues
  -> Snowflake DBT PROJECT object
  -> dbt curated view: <DB>.<DBT_SCHEMA>.github_issues_curated
```

## Why this uses a job service

Snowpark Container Services supports both long-running services and job services.

This demo uses a **job service** because the `dlt` load is a finite batch run: it starts, fetches GitHub issues, writes to Snowflake, and exits. That maps directly to `EXECUTE JOB SERVICE` and is a better fit than keeping a long-running service alive for a one-shot ingestion task.

## Default demo object names

Core data/dbt objects:

- raw database: `DLT_GITHUB_DEMO`
- raw dlt schema/dataset: `github_issues_demo`
- curated dbt schema: `github_issues_analytics`
- curated model: `github_issues_curated`
- dbt project object example name: `github_issues_demo_project`

Snowpark Container Services examples in this repo:

- compute pool: `DLT_GITHUB_DEMO_POOL`
- image repository: `DLT_GITHUB_REPO`
- spec stage: `DLT_GITHUB_CONTAINER_STAGE`
- network rule: `DLT_GITHUB_GH_API_RULE`
- external access integration: `DLT_GITHUB_GH_EAI`
- example job service name: `GITHUB_ISSUES_LOAD_JOB`

## Repository layout

```text
.
├── .github/workflows/manual-load.yml
├── container/
│   ├── Dockerfile
│   └── entrypoint.sh
├── dbt_project.yml
├── models/
│   ├── curated/
│   │   ├── github_issues_curated.sql
│   │   └── schema.yml
│   └── sources.yml
├── profiles/
│   └── profiles.template.yml
├── snowflake/
│   ├── execute_container_job.example.sql
│   ├── github_issues_job.yaml
│   ├── setup_container_demo.sql
│   ├── setup_demo.sql
│   └── validate_demo.sql
├── src/dlthubsnow/
├── tests/
├── pyproject.toml
└── uv.lock
```

Generated dbt outputs (`target/`, `logs/`), local profile/secrets files, and local container override env files stay out of git.

## Setup

### 1) Sync the repo for validation/build tooling

Install [`uv`](https://docs.astral.sh/uv/) first if needed, then sync:

```bash
uv sync --python 3.13
```

This repo uses `uv` for local validation and container build preparation. It does **not** use `uv run dlthubsnow` as the demo runtime path.

### 2) Validate the Snow CLI connection used in this repo

All setup and validation examples use the working Snow CLI connection **`mpz`**:

```bash
snow connection test --connection mpz
```

If you need elevated privileges for setup, pass an explicit role override such as:

```bash
snow sql --connection mpz --role ACCOUNTADMIN -q "select current_role()"
```

`mpz` does not currently provide a default warehouse or database, so the commands in this repo keep those explicit.

### 3) Bootstrap the core warehouse/database/dbt objects

Run the shared setup SQL:

```bash
snow sql --connection mpz --role ACCOUNTADMIN -f snowflake/setup_demo.sql
```

This creates:

- `DLT_GITHUB_DEMO_WH`
- `DLT_GITHUB_DEMO`
- `DLT_GITHUB_DEMO.GITHUB_ISSUES_ANALYTICS`

That curated schema must exist before Snowflake-side dbt compile/execute succeeds.

### 4) Bootstrap the Snowpark Container Services objects

Run the container setup SQL:

```bash
snow sql --connection mpz --role ACCOUNTADMIN -f snowflake/setup_container_demo.sql
```

That file creates:

- the compute pool
- the image repository
- the spec stage
- the GitHub egress network rule
- the external access integration

The compute pool is created with `INITIALLY_SUSPENDED = TRUE` so the setup step itself does not start compute.

### 5) Snowflake auth inside the containerized dlt run

No Snowflake connection secret is required for the `dlt` job running inside Snowpark Container Services.

This repo uses Snowflake's auto-mounted OAuth token inside the container together with `dlt`'s Snowflake destination support for:

- `DESTINATION__SNOWFLAKE__CREDENTIALS__AUTHENTICATOR=oauth`
- `DESTINATION__SNOWFLAKE__CREDENTIALS__DATABASE=<database>`
- `DESTINATION__SNOWFLAKE__CREDENTIALS__WAREHOUSE=<warehouse>`

With `dlt>=1.23.0`, leaving the Snowflake host and token unset is intentional: `dlt` reads `/snowflake/session/token` and the Snowflake-provided environment automatically.

If you want higher GitHub API limits, you can still create an optional `GENERIC_STRING` secret for a GitHub token and add a separate secret mapping in `snowflake/github_issues_job.yaml`.

## Build and publish the container image

The recommended path now matches the reference SPCS repo pattern: **build and publish from GitHub Actions** so developers do not need local Docker just to deploy this demo.

### GitHub Actions path (recommended, no local Docker)

Configure these repository secrets first:

| Secret | Value |
|--------|-------|
| `SNOWFLAKE_ACCOUNT` | Your Snowflake `org-account` identifier |
| `SNOWFLAKE_USER` | The user GitHub Actions should authenticate as |
| `SNOWFLAKE_PRIVATE_KEY` | Base64-encoded RSA private key PEM for that user |
| `SNOWFLAKE_ROLE` | Role with access to the demo image repository, stage, compute pool, warehouse, integration, and job service creation |

Then use the new workflows:

1. Run **`Setup Snowflake SPCS infrastructure`** once. It authenticates with the Snowflake CLI from GitHub Actions and executes:
   - `snowflake/setup_demo.sql`
   - `snowflake/setup_container_demo.sql`
2. Run **`Build and run SPCS job`** whenever you want a load. That workflow:
   - builds the image on the GitHub runner for `linux/amd64`
   - logs into the Snowflake image registry
   - pushes `dlthubsnow:<sha>` and `dlthubsnow:latest`
   - uploads `snowflake/github_issues_job.yaml` to the demo stage
   - executes the SPCS job service and waits for completion using Snowflake-provided OAuth inside the container

The workflow inputs default to the demo object names in this repo, but you can override them at dispatch time.

### Local Docker path (optional manual alternative)

If you prefer to build and push manually from your workstation, the original Docker flow still works.

### 1) Build the image locally

Snowpark Container Services requires a `linux/amd64` image:

```bash
docker buildx build --platform linux/amd64 -f container/Dockerfile -t dlthubsnow:latest --load .
```

The image:

- installs the package with `uv sync --locked --no-dev`
- runs as a non-root user
- starts through `container/entrypoint.sh`
- executes the packaged `dlthubsnow` CLI inside the container

### 2) Authenticate Docker to the Snowflake registry

```bash
snow spcs image-registry login --connection mpz --role ACCOUNTADMIN
```

### 3) Resolve the repository URL and push the image

```bash
snow spcs image-repository url \
  --connection mpz \
  --role ACCOUNTADMIN \
  --database DLT_GITHUB_DEMO \
  --schema PUBLIC \
  DLT_GITHUB_REPO
```

Then tag and push:

```bash
export IMAGE_REPO_URL='<registry>/<db>/<schema>/<repository>'
docker tag dlthubsnow:latest "$IMAGE_REPO_URL/dlthubsnow:latest"
docker push "$IMAGE_REPO_URL/dlthubsnow:latest"
```

## Stage the job specification

Upload the Snowpark Container Services job spec template:

```bash
snow sql --connection mpz --role ACCOUNTADMIN -q "PUT file://$(pwd)/snowflake/github_issues_job.yaml @DLT_GITHUB_DEMO.PUBLIC.DLT_GITHUB_CONTAINER_STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
```

## Execute the dlt load inside Snowflake

Use the provided example SQL file:

```bash
snow sql --connection mpz --role ACCOUNTADMIN -f snowflake/execute_container_job.example.sql
```

That example:

1. drops any prior demo service with the same name
2. runs `EXECUTE JOB SERVICE` asynchronously
3. waits for completion with `!SPCS_WAIT_FOR`
4. describes the job service at the end

Because this is a **job service**, the container exits when the load finishes.

The job spec does **not** mount Snowflake credentials. Instead, `dlt` uses Snowflake's OAuth token injected into the running SPCS container.

## Why incremental reruns still work in a job container

`dlt` restores pipeline state from the destination by default. That means the container does **not** need a persistent local state directory to keep incremental progress across runs.

In practice:

- `_dlt_pipeline_state` lives in Snowflake
- `_dlt_loads` records load history in Snowflake
- a fresh job container can restore state from the destination dataset and continue incrementally

## Validate the raw tables

After a successful job run:

```bash
snow sql --connection mpz --role ACCOUNTADMIN -f snowflake/validate_demo.sql
```

That validates:

- `github_issues` exists
- `_dlt_loads` exists
- `_dlt_pipeline_state` exists

## dbt layer

After the containerized `dlt` load lands raw issues in Snowflake, dbt reads that raw table as a source and builds a single curated view:

- source: `{{ source('github_raw', 'github_issues') }}`
- model: `github_issues_curated`
- default raw schema: `github_issues_demo`
- default curated schema: `github_issues_analytics`

The model intentionally stays small and SQL-only. It derives:

- `is_open`
- `issue_age_days`
- `days_since_update`
- `label_count`

## Deploy and execute dbt in Snowflake

Snowflake dbt Projects require a `profiles.yml`, but Snowflake documentation warns that deployment stops if the committed profile contains passwords.

This repo therefore commits only `profiles/profiles.template.yml`. Create a temporary runtime copy:

```bash
export DBT_PROJECT_NAME='github_issues_demo_project'
export DBT_SNOWFLAKE_ROLE='<role>'
export DBT_SNOWFLAKE_WAREHOUSE='DLT_GITHUB_DEMO_WH'
export DBT_DATABASE='DLT_GITHUB_DEMO'
export DBT_SOURCE_SCHEMA='github_issues_demo'
export DBT_SCHEMA='github_issues_analytics'

tmpdir="$(mktemp -d)"
cp profiles/profiles.template.yml "$tmpdir/profiles.yml"
```

Deploy the DBT PROJECT object:

```bash
snow dbt deploy \
  --connection mpz \
  --database DLT_GITHUB_DEMO \
  --schema GITHUB_ISSUES_ANALYTICS \
  --warehouse DLT_GITHUB_DEMO_WH \
  --role "$DBT_SNOWFLAKE_ROLE" \
  --source . \
  --profiles-dir "$tmpdir" \
  --default-target dev \
  "$DBT_PROJECT_NAME"
```

Execute the curated model:

```bash
snow dbt execute \
  --connection mpz \
  --database DLT_GITHUB_DEMO \
  --schema GITHUB_ISSUES_ANALYTICS \
  --warehouse DLT_GITHUB_DEMO_WH \
  --role "$DBT_SNOWFLAKE_ROLE" \
  "$DBT_PROJECT_NAME" \
  run --select github_issues_curated
```

Clean up the temporary profile:

```bash
rm -rf "$tmpdir"
```

Optional curated-model spot check:

```bash
snow sql --connection mpz --role ACCOUNTADMIN -q "select issue_id, issue_number, is_open, issue_age_days from DLT_GITHUB_DEMO.GITHUB_ISSUES_ANALYTICS.GITHUB_ISSUES_CURATED limit 20"
```

## Local validation only

These local checks exist to validate the repo and Python/dbt assets. They are **not** the supported runtime path for loading data.

```bash
uv run pytest

tmpdir="$(mktemp -d)"
cp profiles/profiles.template.yml "$tmpdir/profiles.yml"
uv run --python 3.13 dbt parse --profiles-dir "$tmpdir"
rm -rf "$tmpdir"

sh -n container/entrypoint.sh
```

If you also want to spot-check the container image locally and already have Docker installed, you can still run:

```bash
docker buildx build --platform linux/amd64 -f container/Dockerfile -t dlthubsnow:ci --load .
```

## GitHub Actions

This repo now has three GitHub Actions workflows:

- `.github/workflows/manual-load.yml` validates the repo (`uv sync`, `pytest`, `dbt parse`, entrypoint syntax, CI image build)
- `.github/workflows/setup-spcs-infra.yml` runs the Snowflake setup SQL from GitHub Actions so you do not need local Docker or local Snow CLI for the one-time bootstrap
- `.github/workflows/deploy-spcs-job.yml` builds the image on the GitHub runner, pushes it to the Snowflake registry, stages the job spec, and executes the job service with Snowflake-provided OAuth inside the container

That means the recommended deployment path no longer depends on local Docker.

## What is still environment-dependent

This repo now contains the assets and docs for the Snowflake-container runtime path, but the following still depend on a live Snowflake environment:

- compute pool creation privileges
- image repository access
- a Docker-capable build environment pushing to the Snowflake registry (the GitHub-hosted runner is the default choice)
- stage upload
- secret creation
- live `EXECUTE JOB SERVICE`
- live `snow dbt deploy` / `snow dbt execute`

## Notes for reviewers

- The `dlt` execution model is now Snowpark Container Services job service only.
- The local Python CLI remains in the repo because the container runs that packaged entrypoint.
- Secrets are intentionally excluded from version control.
- The dbt layer remains intentionally lightweight: one source and one curated model.
