with renamed as (
    select
        upper(trim(to_varchar("City"))) as city,
        try_to_date(to_varchar("Date")) as date,
        try_to_double(to_varchar("PM2.5")) as pm25,
        try_to_double(to_varchar("PM10")) as pm10,
        try_to_double(to_varchar("NO")) as no,
        try_to_double(to_varchar("NO2")) as no2,
        try_to_double(to_varchar("NOx")) as nox,
        try_to_double(to_varchar("NH3")) as nh3,
        try_to_double(to_varchar("CO")) as co,
        try_to_double(to_varchar("SO2")) as so2,
        try_to_double(to_varchar("O3")) as o3,
        try_to_double(to_varchar("Benzene")) as benzene,
        try_to_double(to_varchar("Toluene")) as toluene,
        try_to_double(to_varchar("Xylene")) as xylene,
        try_to_double(to_varchar("AQI")) as aqi_reported,
        nullif(initcap(trim(to_varchar("AQI_Bucket"))), '') as aqi_bucket_reported
    from {{ source('air_quality', 'city_day') }}
), cleaned as (
    select
        *,
        coalesce(aqi_reported < 0 or aqi_reported > 1000, false) as aqi_out_of_range,
        case when aqi_reported between 0 and 1000 then aqi_reported end as aqi,
        case when aqi_reported between 0 and 1000 then aqi_bucket_reported end as aqi_bucket
    from renamed
), deduplicated as (
    select * from cleaned
    qualify row_number() over (
        partition by city, date
        order by aqi_reported desc nulls last, pm25 desc nulls last, pm10 desc nulls last,
                 no, no2, nox, nh3, co, so2, o3, benzene, toluene, xylene, aqi_bucket_reported
    ) = 1
)
select
    city || '|' || to_char(date, 'YYYY-MM-DD') as city_date_key,
    city, date, year(date) as year, month(date) as month,
    pm25, pm10, no, no2, nox, nh3, co, so2, o3, benzene, toluene, xylene,
    aqi_reported, aqi_out_of_range, aqi, aqi_bucket_reported, aqi_bucket
from deduplicated
