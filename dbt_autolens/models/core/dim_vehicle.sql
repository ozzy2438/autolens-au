-- Core model: Vehicle dimension (Kimball star schema)
-- One row per unique vehicle configuration

with distinct_vehicles as (
    select distinct
        brand,
        model,
        body_type,
        fuel_type,
        transmission,
        drive_type,
        doors,
        seats,
        cylinders
    from {{ ref('stg_listings') }}
)

select
    {{ dbt_utils.generate_surrogate_key([
        'brand', 'model', 'body_type', 'fuel_type', 'transmission',
        'drive_type', 'doors', 'seats', 'cylinders'
    ]) }} as vehicle_key,
    brand,
    model,
    
    -- Badge/variant proxy: extract from model string
    -- e.g., "camry ascent" -> variant = "ascent"
    case
        when position(' ' in model) > 0
        then trim(substring(model from position(' ' in model) + 1))
        else null
    end as variant_proxy,
    
    body_type,
    fuel_type,
    transmission,
    drive_type,
    doors,
    seats,
    cylinders,
    
    -- Vehicle segment classification
    case
        when body_type in ('suv', 'wagon') and cylinders >= 6 then 'large_suv'
        when body_type in ('suv') and cylinders < 6 then 'medium_suv'
        when body_type = 'ute' then 'utility'
        when body_type = 'sedan' and cylinders >= 6 then 'large_car'
        when body_type = 'sedan' then 'medium_car'
        when body_type = 'hatchback' then 'small_car'
        when body_type in ('coupe', 'convertible') then 'sports'
        when body_type = 'van' then 'commercial'
        else 'other'
    end as vehicle_segment

from distinct_vehicles
