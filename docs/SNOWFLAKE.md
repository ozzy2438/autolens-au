# Snowflake Operations

AutoLens AU uses Snowflake for production data and a separate transient database
for real Snowflake CI integration. Local and pull-request tests keep PostgreSQL as
a secretless compatibility backend; production refreshes never use it.

## Account objects

| Object | Purpose |
|---|---|
| `AUTOLENS_WH` | Shared X-Small, single-cluster compute with 60-second auto-suspend |
| `AUTOLENS_AU` | Production database with one-day Time Travel retention |
| `AUTOLENS_AU_CI` | Transient CI database with zero-day retention |
| `RAW` | Source-aligned ingestion tables |
| `STAGING` | Cleaned dbt views |
| `CORE` | Conformed dbt facts and dimensions |
| `MARTS` | Application-facing analytical tables/views |

All data schemas are managed-access schemas. Their `AUTOLENS_ADMIN` owner, or an
account role with `MANAGE GRANTS`, controls object grants; table/view creators
cannot widen access independently.

## Role boundaries

| Role | Production access | CI access | Intended identity |
|---|---|---|---|
| `AUTOLENS_INGEST` | Write/create in `RAW` | None | Functional child role |
| `AUTOLENS_TRANSFORM` | Read `RAW`; create in `STAGING`, `CORE`, `MARTS` | None | Functional child role |
| `AUTOLENS_PIPELINE` | Inherits ingest + transform | None | Monthly refresh service |
| `AUTOLENS_APP` | Read `RAW`, `CORE`, `MARTS`; no writes | None | Streamlit/FastAPI service |
| `AUTOLENS_CI` | None | Build/read all four CI schemas | GitHub Actions CI service |
| `AUTOLENS_ADMIN` | Owns project containers and inherits all project roles | Owns | Human project administration |

`AUTOLENS_APP` can read `RAW` because the current dashboard reports source
freshness and market-monitor data directly. It intentionally cannot read
`STAGING` or create any object. Schema-level future grants automatically expose
new eligible tables/views without granting broader schema privileges.

## Reapplying the account bootstrap

[`infra/snowflake/bootstrap.sql`](../infra/snowflake/bootstrap.sql) contains no
credentials and is safe to keep in version control. Run it from a temporary
Snowflake CLI connection as a user that currently holds `ACCOUNTADMIN`:

```bash
export SNOWFLAKE_PASSWORD='set-this-in-your-shell-or-secret-manager'
snow sql --temporary-connection \
  --account your_org-your_account \
  --user your_admin_user \
  --role ACCOUNTADMIN \
  --filename infra/snowflake/bootstrap.sql
unset SNOWFLAKE_PASSWORD
```

The script assigns project roles to `CURRENT_USER()`, changes that user's default
role to `AUTOLENS_ADMIN`, and leaves `ACCOUNTADMIN` available only for account-level
administration. It does not create a resource monitor because a credit quota is a
budget decision, kept separate from access control (see below).

## Credit resource monitor

[`infra/snowflake/resource_monitor.sql`](../infra/snowflake/resource_monitor.sql)
creates `AUTOLENS_MONITOR`, a monthly credit cap bound to `AUTOLENS_WH`. It is kept
out of the account bootstrap on purpose: the bootstrap defines *who can do what*, and
the monitor defines *how much it may cost*, which is a budget decision to make
explicitly. Run it as `ACCOUNTADMIN` after choosing a ceiling:

```bash
export SNOWFLAKE_PASSWORD='set-this-in-your-shell-or-secret-manager'
snow sql --temporary-connection \
  --account your_org-your_account \
  --user your_admin_user \
  --role ACCOUNTADMIN \
  --filename infra/snowflake/resource_monitor.sql
unset SNOWFLAKE_PASSWORD
```

The default `CREDIT_QUOTA` is 5 credits/month — a conservative cap for one X-Small
warehouse serving monthly refreshes, CI, and light dashboard reads. Triggers `SUSPEND`
at 100% (running statements finish, new ones are blocked) and `SUSPEND_IMMEDIATE` at
110%; suspension is enforced regardless of notification setup. The 75% and 90% `NOTIFY`
triggers only send email once you uncomment `NOTIFY_USERS` and list users with a
verified email and notifications enabled.

The file is idempotent by using `CREATE ... IF NOT EXISTS`: a rerun is a no-op and
never resets the current period's accumulated usage. Because a rerun therefore ignores
edits to the `CREATE`, change the ceiling later with an explicit
`ALTER RESOURCE MONITOR AUTOLENS_MONITOR SET CREDIT_QUOTA = <new_value>` (shown at the
bottom of the file), which does not reset usage. Snowflake does not allow `OR REPLACE`
together with `IF NOT EXISTS`, and `OR REPLACE` would recreate the monitor, so it is
avoided here.

## Non-human authentication

Use Snowflake `TYPE=SERVICE` users with 2048-bit or stronger RSA key pairs. Never
use the human administrator or a password in GitHub Actions, Streamlit Cloud, or
Render. Assign only one direct runtime role to each service user:

- `AUTOLENS_CI_SVC` → `AUTOLENS_CI`
- `AUTOLENS_PIPELINE_SVC` → `AUTOLENS_PIPELINE`
- a deployment-specific dashboard/API user → `AUTOLENS_APP`

The repository consumes PKCS#8 PEM keys from environment secrets. A local file can
be supplied as `SNOWFLAKE_PRIVATE_KEY_PATH`; hosted systems should inject the PEM
as `SNOWFLAKE_PRIVATE_KEY`. If a key is encrypted, also set
`SNOWFLAKE_PRIVATE_KEY_PASSPHRASE`.

## GitHub configuration

Repository variable:

- `SNOWFLAKE_ACCOUNT`: organization-account identifier

Repository secrets:

- `SNOWFLAKE_CI_USER`
- `SNOWFLAKE_CI_PRIVATE_KEY`
- `SNOWFLAKE_CI_PRIVATE_KEY_PASSPHRASE` only when the key is encrypted
- `SNOWFLAKE_PIPELINE_USER`
- `SNOWFLAKE_PIPELINE_PRIVATE_KEY`
- `SNOWFLAKE_PIPELINE_PRIVATE_KEY_PASSPHRASE` only when the key is encrypted

The required PR dbt gate remains PostgreSQL-backed so forked PRs receive no
Snowflake secret. Same-repository PRs and every push to `main` also run a real
seed-backed dbt build in `AUTOLENS_AU_CI`; scheduled refreshes use `AUTOLENS_AU`
with `AUTOLENS_PIPELINE`. Query tags include the GitHub run ID for auditability.

## Streamlit and FastAPI settings

Configure each deployed service with a dedicated `AUTOLENS_APP` service user and:

```text
DATABASE_BACKEND=snowflake
SNOWFLAKE_ACCOUNT=your_org-your_account
SNOWFLAKE_USER=your_app_service_user
SNOWFLAKE_PRIVATE_KEY=<PKCS8 PEM secret>
SNOWFLAKE_DATABASE=AUTOLENS_AU
SNOWFLAKE_SCHEMA=RAW
SNOWFLAKE_WAREHOUSE=AUTOLENS_WH
SNOWFLAKE_ROLE=AUTOLENS_APP
```

The application engine sets a Snowflake query tag, uses connection pre-ping, and
loads private-key material only in memory. `AUTOLENS_WH` auto-resumes for a query
and suspends after 60 seconds of inactivity.

## Rotation and checks

Snowflake supports two public-key slots (`RSA_PUBLIC_KEY` and
`RSA_PUBLIC_KEY_2`). Rotate without downtime by setting the second public key,
updating the external secret, verifying the new key, and then removing the old
key. Validate role boundaries with secondary roles disabled; otherwise a human
administrator's additional active roles can make a negative permission test give
a false result.
