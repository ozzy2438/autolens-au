-- Core model: Fact table for vehicle listings (Kimball star schema)
-- Grain: one row per vehicle listing

with listings as (
    select * from {{ ref('stg_listings') }}
),

locations as (
    select * from {{ ref('dim_location') }}
),

final as (
    select
        -- Keys
        l.listing_id,
        {{ dbt_utils.generate_surrogate_key([
            'l.brand', 'l.model', 'l.variant', 'l.body_type', 'l.fuel_type', 'l.transmission',
            'l.drive_type', 'l.doors', 'l.seats', 'l.cylinders'
        ]) }} as vehicle_key,
        loc.location_key,
        
        l.manufacture_year,
        l.listing_snapshot_date,
        
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
    left join locations loc
        on l.location_raw = loc.location_raw
)

select * from final
