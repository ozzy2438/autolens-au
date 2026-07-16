-- Staging model: NSW Fuel price data
-- Source: raw.raw_fuel_prices (NSW FuelCheck API)

with source as (
    select * from {{ source('raw', 'raw_fuel_prices') }}
),

cleaned as (
    select
        stationcode as station_code,
        fueltype as fuel_type_code,
        cast(price as numeric) / 100.0 as price_per_litre,  -- API returns cents per litre
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
        -- Documented plausibility window, not silent dropping: the live feed of
        -- ~10k station prices occasionally carries mis-keyed readings (a handful
        -- per refresh). Retail fuel outside 50-500 cents/litre is treated as an
        -- invalid reading; the downstream accepted_range test (0.5-5.0 $/L)
        -- enforces this contract on everything staging emits.
        and cast(price as numeric) between 50 and 500
)

select * from cleaned
