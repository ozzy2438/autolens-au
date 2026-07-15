-- Custom test: Check for price outliers using IQR method
-- Prices outside 3x IQR from Q1/Q3 are flagged

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

-- Test passes if fewer than 1% of records are extreme outliers
select count(*) as outlier_count
from outliers
having count(*) > (select count(*) * 0.01 from {{ ref('stg_listings') }})
