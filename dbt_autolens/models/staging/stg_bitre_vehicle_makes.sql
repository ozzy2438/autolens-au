-- National registered-vehicle counts by make from BITRE Road Vehicles Australia

select
    trim(lower(make)) as make,
    cast(reference_year as integer) as reference_year,
    cast(registered_vehicles as bigint) as registered_vehicles,
    source as data_source,
    fetched_at
from {{ source('raw', 'raw_bitre_vehicle_makes') }}
where make is not null
  and registered_vehicles is not null
  and cast(registered_vehicles as bigint) >= 0
