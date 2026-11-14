select city_date_key
from {{ ref('stg_city_day') }}
where aqi_out_of_range != coalesce(aqi_reported < 0 or aqi_reported > 1000, false)
   or (aqi_out_of_range and (aqi is not null or aqi_bucket is not null))
   or (aqi_reported between 0 and 1000 and (aqi is null or aqi != aqi_reported))
   or (aqi_reported is null and aqi is not null)
