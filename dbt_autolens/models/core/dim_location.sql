-- Core model: Location dimension (Kimball star schema)
-- One row per unique location

with distinct_locations as (
    select distinct
        location_raw
    from {{ ref('stg_listings') }}
    where location_raw is not null
)

select
    {{ dbt_utils.generate_surrogate_key(['location_raw']) }} as location_key,
    location_raw,
    
    -- Extract state from location string
    case
        when location_raw ~* 'NSW|New South Wales|Sydney' then 'NSW'
        when location_raw ~* 'VIC|Victoria|Melbourne' then 'VIC'
        when location_raw ~* 'QLD|Queensland|Brisbane' then 'QLD'
        when location_raw ~* 'WA|Western Australia|Perth' then 'WA'
        when location_raw ~* 'SA|South Australia|Adelaide' then 'SA'
        when location_raw ~* 'TAS|Tasmania|Hobart' then 'TAS'
        when location_raw ~* 'ACT|Canberra' then 'ACT'
        when location_raw ~* 'NT|Northern Territory|Darwin' then 'NT'
        else 'Unknown'
    end as state,
    
    -- Extract city/suburb if possible
    case
        when location_raw ~* 'Sydney' then 'Sydney'
        when location_raw ~* 'Melbourne' then 'Melbourne'
        when location_raw ~* 'Brisbane' then 'Brisbane'
        when location_raw ~* 'Perth' then 'Perth'
        when location_raw ~* 'Adelaide' then 'Adelaide'
        when location_raw ~* 'Hobart' then 'Hobart'
        when location_raw ~* 'Canberra' then 'Canberra'
        when location_raw ~* 'Darwin' then 'Darwin'
        else trim(split_part(location_raw, ',', 1))
    end as city,
    
    -- Metro vs regional classification
    case
        when location_raw ~* 'Sydney|Melbourne|Brisbane|Perth|Adelaide|Hobart|Canberra|Darwin'
        then 'Metropolitan'
        else 'Regional'
    end as metro_regional

from distinct_locations
