# Streamlit Cloud Deployment

The dashboard is the single public surface: it reads Snowflake directly with the
read-only `AUTOLENS_APP` role and loads the calibrated model straight from the
newest `model-*` GitHub release, so no separate API deployment is required to
demonstrate the product. (The FastAPI container remains available on GHCR as a
later enhancement.)

## 1. Create the read-only service identity (one-time, ACCOUNTADMIN)

Generate a key pair locally and run
[`infra/snowflake/app_service_user.sql`](../infra/snowflake/app_service_user.sql)
with the public key filled in:

```bash
export SNOWFLAKE_PASSWORD='set-this-in-your-shell-or-secret-manager'
snow sql --temporary-connection \
  --account UFHWVHU-LI47624 \
  --user <your_admin_user> \
  --role ACCOUNTADMIN \
  --filename infra/snowflake/app_service_user.sql
unset SNOWFLAKE_PASSWORD
```

The private key never enters this repository or GitHub; it goes only into the
Streamlit Cloud secret store.

## 2. Create the Streamlit Cloud app

At [share.streamlit.io](https://share.streamlit.io) → **Create app**:

| Setting | Value |
|---|---|
| Repository | `ozzy2438/autolens-au` |
| Branch | `main` |
| Main file path | `src/dashboard/app.py` |
| Python version (Advanced settings) | `3.11` |

Dependencies install from `requirements.txt`, which is exported from `uv.lock`
and already includes the Snowflake stack.

## 3. Configure secrets

App → **Settings → Secrets**, paste:

```toml
DATABASE_BACKEND = "snowflake"
SNOWFLAKE_ACCOUNT = "UFHWVHU-LI47624"
SNOWFLAKE_USER = "AUTOLENS_APP_SVC"
SNOWFLAKE_DATABASE = "AUTOLENS_AU"
SNOWFLAKE_SCHEMA = "RAW"
SNOWFLAKE_WAREHOUSE = "AUTOLENS_WH"
SNOWFLAKE_ROLE = "AUTOLENS_APP"
SNOWFLAKE_QUERY_TAG = "autolens_dashboard"
MODEL_RELEASE_REPOSITORY = "ozzy2438/autolens-au"
SNOWFLAKE_PRIVATE_KEY = """
-----BEGIN PRIVATE KEY-----
...your PKCS#8 key...
-----END PRIVATE KEY-----
"""
# Optional but recommended: a fine-grained read-only GitHub token so release
# downloads never hit anonymous API rate limits on shared egress IPs.
# GITHUB_TOKEN = "github_pat_..."
```

Every dashboard entry script bridges root-level Streamlit secrets into the
environment before configuration is read
([`src/dashboard/runtime.py`](../src/dashboard/runtime.py)), so the same code
runs unchanged locally and on Streamlit Cloud.

## 4. Verify and register the deployment

1. Open the app URL: the landing page shows the latest measured refresh and
   model metrics; Instant Valuation must report a loaded calibrated model.
2. Make the app public (Settings → Sharing) so it is verifiable from a CV.
3. Register the URL so the six-hourly health workflow starts verifying it:

```bash
gh variable set DASHBOARD_URL --repo ozzy2438/autolens-au --body "https://<app>.streamlit.app"
```

4. Only after the Deployment Health workflow passes, add the URL to README and
   STATUS.md.

## Operational notes

- The app resumes `AUTOLENS_WH` on queries; `st.cache_data(ttl=300)` keeps
  warehouse wake-ups infrequent and the `AUTOLENS_MONITOR` resource monitor caps
  monthly spend.
- The model artifact is cached per process; a newly released model is picked up
  on app restart (Streamlit Cloud restarts on redeploys and inactivity cycles).
- Key rotation: Snowflake supports a second key slot (`RSA_PUBLIC_KEY_2`); see
  [SNOWFLAKE.md](SNOWFLAKE.md#rotation-and-checks).
