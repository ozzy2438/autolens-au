-- Staging model: QLD Vehicle Registration data
-- Source: raw.raw_qld_registrations (QLD Open Data Portal)

with source as (
    select * from {{ source('raw', 'raw_qld_registrations') }}
),

cleaned as (
    select
        trim(lower(make)) as make,
        trim(lower(model)) as model,
        cast(year as integer) as manufacture_year,
        trim(lower(body_type)) as body_type,
        trim(lower(fuel_type)) as fuel_type,
        trim(lower(colour)) as colour,
        trim(lower(vehicle_category)) as vehicle_category,
        source as data_source,
        ingested_at
    from source
    where make is not null
)

select * from cleaned
