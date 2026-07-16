-- AutoLens AU Snowflake credit resource monitor
--
-- Run this file as ACCOUNTADMIN, separately from bootstrap.sql. The account
-- bootstrap intentionally omits a resource monitor because a credit quota is a
-- budget decision, not an access-control one. This file makes that decision
-- explicit, reviewable, and re-runnable.
--
-- Adjust CREDIT_QUOTA to the monthly ceiling you are willing to spend. The
-- default of 5 credits/month is a conservative cap for a single X-Small
-- warehouse used for monthly refreshes, CI, and light dashboard reads.
--
-- Triggers escalate from notification to suspension. NOTIFY informs account
-- administrators (configure notification recipients in the Snowflake UI or via
-- NOTIFICATION INTEGRATION). SUSPEND lets running statements finish but blocks
-- new ones; SUSPEND_IMMEDIATE kills running statements to guarantee the ceiling.

USE ROLE ACCOUNTADMIN;

CREATE RESOURCE MONITOR IF NOT EXISTS AUTOLENS_MONITOR
    WITH
        CREDIT_QUOTA = 5
        FREQUENCY = MONTHLY
        START_TIMESTAMP = IMMEDIATELY
        TRIGGERS
            ON 75 PERCENT DO NOTIFY
            ON 90 PERCENT DO NOTIFY
            ON 100 PERCENT DO SUSPEND
            ON 110 PERCENT DO SUSPEND_IMMEDIATE;

-- Reapplying with ALTER makes the quota and triggers converge without replacing
-- the monitor, so accumulated usage in the current period is preserved.
ALTER RESOURCE MONITOR AUTOLENS_MONITOR SET
    CREDIT_QUOTA = 5
    FREQUENCY = MONTHLY
    START_TIMESTAMP = IMMEDIATELY
    TRIGGERS
        ON 75 PERCENT DO NOTIFY
        ON 90 PERCENT DO NOTIFY
        ON 100 PERCENT DO SUSPEND
        ON 110 PERCENT DO SUSPEND_IMMEDIATE;

-- Bind the monitor to the only warehouse in the account. A warehouse can have at
-- most one resource monitor; this assignment is idempotent.
ALTER WAREHOUSE AUTOLENS_WH SET RESOURCE_MONITOR = AUTOLENS_MONITOR;
