-- QLD new-registration and transfer activity (not total active fleet)

with source as (
    select * from {{ source('raw', 'raw_qld_registration_activity') }}
),

cleaned as (
    select
        cast(activity_month as date) as activity_month,
        trim(lower(make)) as make,
        nullif(trim(lower(model)), '') as model,
        nullif(trim(lower(badge)), '') as badge,
        nullif(trim(lower(body_shape)), '') as body_shape,
        nullif(trim(lower(fuel_type)), '') as fuel_type,
        trim(lower(transaction_type)) as transaction_type,
        cast(activity_count as bigint) as activity_count,
        source_resource_id,
        source as data_source,
        fetched_at
    from source
    where make is not null
      and activity_count is not null
      and cast(activity_count as bigint) > 0
)

select * from cleaned
