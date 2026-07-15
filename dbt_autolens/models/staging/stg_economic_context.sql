-- Official RBA-published CPI observations

select
    cast(period_date as date) as period_date,
    period as quarter,
    cast(cpi_index as numeric) as cpi_index,
    source as data_source,
    fetched_at
from {{ source('raw', 'raw_cpi') }}
where cpi_index is not null
