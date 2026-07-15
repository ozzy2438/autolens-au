-- Staging model: NSW Fuel price data
-- Source: raw.raw_fuel_prices (NSW FuelCheck API)

with source as (
    select * from {{ source('raw', 'raw_fuel_prices') }}
),

cleaned as (
    select
        stationcode as station_code,
        fueltype as fuel_type_code,
        cast(price as numeric) / 10.0 as price_per_litre,  -- API returns price in tenths of cents
        lastupdated as last_updated,
        name as station_name,
        suburb,
        state,
        cast(latitude as numeric) as latitude,
        cast(longitude as numeric) as longitude,
        fetched_at,
        source as data_source
    from source
    where 
        price is not null
        and cast(price as numeric) > 0
)

select * from cleaned
