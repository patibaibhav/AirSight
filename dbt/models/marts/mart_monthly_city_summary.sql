select
    city || '|' || to_char(date_trunc('month', date), 'YYYY-MM-DD') as city_month_key,
    city,
    date_trunc('month', date)::date as month_start,
    avg(aqi) as avg_aqi,
    max(aqi) as max_aqi,
    avg(pm25) as avg_pm25,
    avg(pm10) as avg_pm10,
    avg(no2) as avg_no2,
    avg(o3) as avg_o3,
    avg(co) as avg_co,
    count(*) as days_recorded,
    count(aqi) as days_measured,
    count_if(aqi_out_of_range) as excluded_aqi_days,
    count_if(aqi_reported is null) as missing_aqi_days,
    count_if(aqi is not null and aqi_bucket in ('Poor', 'Very Poor', 'Severe'))
        / nullif(count(aqi), 0)::float as unhealthy_day_share
from {{ ref('stg_city_day') }}
group by city, date_trunc('month', date)
