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
        when {{ regex_matches('location_raw', 'NSW|New South Wales|Sydney') }} then 'NSW'
        when {{ regex_matches('location_raw', 'VIC|Victoria|Melbourne') }} then 'VIC'
        when {{ regex_matches('location_raw', 'QLD|Queensland|Brisbane') }} then 'QLD'
        when {{ regex_matches('location_raw', 'WA|Western Australia|Perth') }} then 'WA'
        when {{ regex_matches('location_raw', 'SA|South Australia|Adelaide') }} then 'SA'
        when {{ regex_matches('location_raw', 'TAS|Tasmania|Hobart') }} then 'TAS'
        when {{ regex_matches('location_raw', 'ACT|Canberra') }} then 'ACT'
        when {{ regex_matches('location_raw', 'NT|Northern Territory|Darwin') }} then 'NT'
        else 'Unknown'
    end as state,
    
    -- Extract city/suburb if possible
    case
        when {{ regex_matches('location_raw', 'Sydney') }} then 'Sydney'
        when {{ regex_matches('location_raw', 'Melbourne') }} then 'Melbourne'
        when {{ regex_matches('location_raw', 'Brisbane') }} then 'Brisbane'
        when {{ regex_matches('location_raw', 'Perth') }} then 'Perth'
        when {{ regex_matches('location_raw', 'Adelaide') }} then 'Adelaide'
        when {{ regex_matches('location_raw', 'Hobart') }} then 'Hobart'
        when {{ regex_matches('location_raw', 'Canberra') }} then 'Canberra'
        when {{ regex_matches('location_raw', 'Darwin') }} then 'Darwin'
        else trim(split_part(location_raw, ',', 1))
    end as city,
    
    -- Metro vs regional classification
    case
        when {{ regex_matches(
            'location_raw',
            'Sydney|Melbourne|Brisbane|Perth|Adelaide|Hobart|Canberra|Darwin'
        ) }}
        then 'Metropolitan'
        else 'Regional'
    end as metro_regional

from distinct_locations
