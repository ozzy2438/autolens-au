-- Core model: Date dimension (Kimball star schema)
-- One row per date from 1990 to 2030

with date_spine as (
    {{ dbt_utils.date_spine(
        datepart="year",
        start_date="cast('1990-01-01' as date)",
        end_date="cast('2030-01-01' as date)"
    ) }}
)

select
    cast(extract(year from date_year) as integer) as year_key,
    date_year as year_date,
    cast(extract(year from date_year) as integer) as calendar_year,
    
    -- Useful groupings for analysis
    case
        when extract(year from date_year) >= 2020 then 'post-covid'
        when extract(year from date_year) >= 2015 then '2015-2019'
        when extract(year from date_year) >= 2010 then '2010-2014'
        when extract(year from date_year) >= 2005 then '2005-2009'
        when extract(year from date_year) >= 2000 then '2000-2004'
        else 'pre-2000'
    end as era,
    
    -- Age bands for grouping
    case
        when extract(year from current_date) - extract(year from date_year) <= 3 then 'Nearly New (0-3yr)'
        when extract(year from current_date) - extract(year from date_year) <= 7 then 'Young (4-7yr)'
        when extract(year from current_date) - extract(year from date_year) <= 12 then 'Mature (8-12yr)'
        else 'Older (13yr+)'
    end as age_band

from date_spine
