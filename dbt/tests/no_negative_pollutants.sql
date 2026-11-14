select city_date_key
from {{ ref('stg_city_day') }}
where pm25 < 0 or pm10 < 0 or no < 0 or no2 < 0 or nox < 0 or nh3 < 0
   or co < 0 or so2 < 0 or o3 < 0 or benzene < 0 or toluene < 0 or xylene < 0
