-- Staging model: Clean and standardise raw vehicle listings
-- Source: raw.raw_listings (combined Kaggle datasets)

with source as (
    select * from {{ source('raw', 'raw_listings') }}
),

renamed as (
    select
        -- Generate surrogate key
        {{ dbt_utils.generate_surrogate_key(['brand', 'model', 'year', 'kilometres', 'price']) }} as listing_id,
        
        -- Vehicle attributes
        trim(lower(brand)) as brand,
        trim(lower(model)) as model,
        cast(year as integer) as manufacture_year,
        cast(kilometres as numeric) as kilometres,
        trim(lower(body_type)) as body_type,
        trim(lower(fuel_type)) as fuel_type,
        trim(lower(transmission)) as transmission,
        trim(lower(drive_type)) as drive_type,
        cast(doors as integer) as doors,
        cast(seats as integer) as seats,
        cast(cylinders as integer) as cylinders,
        
        -- Condition and listing type
        trim(lower(condition)) as listing_condition,
        
        -- Location
        trim(location) as location_raw,
        
        -- Price (target variable)
        cast(price as numeric) as price_aud,
        
        -- Metadata
        source as data_source,
        ingested_at,
        
        -- Derived: vehicle age
        extract(year from current_date) - cast(year as integer) as vehicle_age
    
    from source
    where 
        price is not null
        and cast(price as numeric) > 1000
        and cast(price as numeric) < 500000
        and year is not null
        and cast(year as integer) >= 1980
        and cast(year as integer) <= extract(year from current_date) + 1
)

select * from renamed
