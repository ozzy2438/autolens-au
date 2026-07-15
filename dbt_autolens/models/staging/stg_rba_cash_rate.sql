-- Official RBA cash-rate target observations

select
    cast(period_date as date) as period_date,
    cast(cash_rate_target_pct as numeric) as cash_rate_target_pct,
    source as data_source,
    fetched_at
from {{ source('raw', 'raw_rba_cash_rate') }}
where cash_rate_target_pct is not null
