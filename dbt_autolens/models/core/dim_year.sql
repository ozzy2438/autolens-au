-- Year dimension for vehicle manufacture-year analysis

with year_spine as (
    {{ dbt_utils.date_spine(
        datepart="year",
        start_date="cast('1980-01-01' as date)",
        end_date="cast('2031-01-01' as date)"
    ) }}
)

select
    cast(extract(year from date_year) as integer) as year_key,
    date_year as year_date,
    cast(extract(year from date_year) as integer) as calendar_year,
    case
        when extract(year from date_year) >= 2020 then 'post-2020'
        when extract(year from date_year) >= 2015 then '2015-2019'
        when extract(year from date_year) >= 2010 then '2010-2014'
        when extract(year from date_year) >= 2005 then '2005-2009'
        when extract(year from date_year) >= 2000 then '2000-2004'
        else 'pre-2000'
    end as era
from year_spine
