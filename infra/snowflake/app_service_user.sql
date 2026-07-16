-- AutoLens AU dashboard/API service identity (template)
--
-- Run once as ACCOUNTADMIN after generating an RSA key pair locally:
--
--   openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out app_rsa_key.p8 -nocrypt
--   openssl rsa -in app_rsa_key.p8 -pubout -out app_rsa_key.pub
--
-- Replace <PUBLIC_KEY_BODY> with the contents of app_rsa_key.pub WITHOUT the
-- BEGIN/END lines and with no line breaks. The private key never enters this
-- repository: it goes only into the deployment platform's secret store
-- (Streamlit Cloud secrets as SNOWFLAKE_PRIVATE_KEY).

USE ROLE ACCOUNTADMIN;

CREATE USER IF NOT EXISTS AUTOLENS_APP_SVC
    TYPE = SERVICE
    DEFAULT_ROLE = AUTOLENS_APP
    DEFAULT_WAREHOUSE = AUTOLENS_WH
    DEFAULT_NAMESPACE = 'AUTOLENS_AU.RAW'
    COMMENT = 'Streamlit dashboard read-only service identity';

ALTER USER AUTOLENS_APP_SVC SET RSA_PUBLIC_KEY = '<PUBLIC_KEY_BODY>';

GRANT ROLE AUTOLENS_APP TO USER AUTOLENS_APP_SVC;
