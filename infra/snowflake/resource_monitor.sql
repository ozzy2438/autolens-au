-- AutoLens AU Snowflake credit resource monitor
--
-- Run this file as ACCOUNTADMIN, separately from bootstrap.sql. The account
-- bootstrap intentionally omits a resource monitor because a credit quota is a
-- budget decision, not an access-control one. This file makes that decision
-- explicit, reviewable, and re-runnable.
--
-- Idempotency: CREATE ... IF NOT EXISTS makes a rerun a no-op that never resets
-- the current period's accumulated usage. (Per Snowflake, OR REPLACE and
-- IF NOT EXISTS are mutually exclusive; OR REPLACE would recreate the monitor.)
-- To change the quota or triggers after creation, run the ALTER shown at the
-- bottom rather than editing and rerunning this CREATE, which a rerun ignores.
--
-- Suspension is enforced by the SUSPEND / SUSPEND_IMMEDIATE triggers regardless
-- of NOTIFY_USERS. The NOTIFY triggers only send email once NOTIFY_USERS lists
-- users who have a verified email and notifications enabled, so that line is
-- left commented for the operator to complete.

USE ROLE ACCOUNTADMIN;

CREATE RESOURCE MONITOR IF NOT EXISTS AUTOLENS_MONITOR
    WITH
        CREDIT_QUOTA = 5
        FREQUENCY = MONTHLY
        START_TIMESTAMP = IMMEDIATELY
        -- NOTIFY_USERS = ( YOUR_ADMIN_USER )   -- set to enable the 75%/90% emails
        TRIGGERS
            ON 75 PERCENT DO NOTIFY
            ON 90 PERCENT DO NOTIFY
            ON 100 PERCENT DO SUSPEND
            ON 110 PERCENT DO SUSPEND_IMMEDIATE;

-- Bind the monitor to the only warehouse in the account. A warehouse has at most
-- one resource monitor; assigning the same monitor again is a no-op.
ALTER WAREHOUSE AUTOLENS_WH SET RESOURCE_MONITOR = AUTOLENS_MONITOR;

-- To raise or lower the ceiling later without resetting the current period, run:
--   ALTER RESOURCE MONITOR AUTOLENS_MONITOR SET CREDIT_QUOTA = <new_value>;
