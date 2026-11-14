select city_date_key
from {{ ref('stg_city_day') }}
where pm25 > 1500 or aqi < 0 or aqi > 1000 or date > current_date()
