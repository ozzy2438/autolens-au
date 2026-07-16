-- Custom data-quality monitor: extreme price outliers via the IQR method.
-- A real used-car market has a legitimate luxury/exotic tail beyond 3x IQR, so a
-- modest outlier share is expected. This is a WARN-severity monitor, not a hard
-- gate: it surfaces on the data-quality log and only fires when the outlier share
-- is high enough to suggest an ingestion/parsing problem rather than market spread.
{{ config(severity='warn') }}

with stats as (
    select
        percentile_cont(0.25) within group (order by price_aud) as q1,
        percentile_cont(0.75) within group (order by price_aud) as q3
    from {{ ref('stg_listings') }}
),

bounds as (
    select
        q1 - 3.0 * (q3 - q1) as lower_bound,
        q3 + 3.0 * (q3 - q1) as upper_bound
    from stats
),

outliers as (
    select
        l.listing_id,
        l.price_aud
    from {{ ref('stg_listings') }} l
    cross join bounds b
    where l.price_aud < b.lower_bound
       or l.price_aud > b.upper_bound
)

-- Warns when more than 5% of records fall beyond 3x IQR — well above the
-- expected luxury tail, so a breach points at a data problem worth investigating.
select count(*) as outlier_count
from outliers
having count(*) > (select count(*) * 0.05 from {{ ref('stg_listings') }})
