{{ config(severity='warn') }}
-- Preserve source readings; report exclusions without blocking the pipeline.
select city_date_key, aqi_reported
from {{ ref('stg_city_day') }}
where aqi_out_of_range
