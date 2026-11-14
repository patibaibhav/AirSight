with renamed as (
    {% set original_headers = ['City', 'Date', 'PM2.5', 'PM10', 'NO', 'NO2', 'NOx', 'NH3', 'CO', 'SO2', 'O3', 'Benzene', 'Toluene', 'Xylene', 'AQI', 'AQI_Bucket'] %}
    {% set raw = namespace(columns=[]) %}
    {% for header in original_headers %}
        {% do raw.columns.append(adapter.quote(header | upper)) %}
    {% endfor %}
    select
        upper(trim(to_varchar({{ raw.columns[0] }}))) as city,
        try_to_date(to_varchar({{ raw.columns[1] }})) as date,
        try_to_double(to_varchar({{ raw.columns[2] }})) as pm25,
        try_to_double(to_varchar({{ raw.columns[3] }})) as pm10,
        try_to_double(to_varchar({{ raw.columns[4] }})) as no,
        try_to_double(to_varchar({{ raw.columns[5] }})) as no2,
        try_to_double(to_varchar({{ raw.columns[6] }})) as nox,
        try_to_double(to_varchar({{ raw.columns[7] }})) as nh3,
        try_to_double(to_varchar({{ raw.columns[8] }})) as co,
        try_to_double(to_varchar({{ raw.columns[9] }})) as so2,
        try_to_double(to_varchar({{ raw.columns[10] }})) as o3,
        try_to_double(to_varchar({{ raw.columns[11] }})) as benzene,
        try_to_double(to_varchar({{ raw.columns[12] }})) as toluene,
        try_to_double(to_varchar({{ raw.columns[13] }})) as xylene,
        try_to_double(to_varchar({{ raw.columns[14] }})) as aqi_reported,
        nullif(initcap(trim(to_varchar({{ raw.columns[15] }}))), '') as aqi_bucket_reported
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
