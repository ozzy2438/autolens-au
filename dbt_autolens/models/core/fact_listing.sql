-- Core model: Fact table for vehicle listings (Kimball star schema)
-- Grain: one row per vehicle listing

with listings as (
    select * from {{ ref('stg_listings') }}
),

vehicles as (
    select * from {{ ref('dim_vehicle') }}
),

locations as (
    select * from {{ ref('dim_location') }}
),

final as (
    select
        -- Keys
        l.listing_id,
        v.vehicle_key,
        loc.location_key,
        
        -- Date dimension (simplified - using manufacture_year as date key)
        l.manufacture_year as listing_year,
        
        -- Measures
        l.price_aud,
        l.kilometres,
        l.vehicle_age,
        
        -- Calculated measures
        case 
            when l.vehicle_age > 0 then l.kilometres / l.vehicle_age
            else l.kilometres
        end as avg_annual_km,
        
        l.vehicle_age * coalesce(l.kilometres, 0) / 10000.0 as age_km_interaction,
        
        -- Descriptive
        l.listing_condition,
        l.data_source,
        l.ingested_at
    
    from listings l
    left join vehicles v
        on l.brand = v.brand
        and l.model = v.model
        and l.body_type = v.body_type
        and l.fuel_type = v.fuel_type
        and l.transmission = v.transmission
    left join locations loc
        on l.location_raw = loc.location_raw
)

select * from final
