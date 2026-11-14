with daily as (
    select city, date_trunc('month', date)::date as month_start,
        count(*) as days_recorded, count(aqi) as days_measured, avg(aqi) as avg_aqi,
        count_if(aqi_out_of_range) as excluded_aqi_days,
        count_if(aqi_reported is null) as missing_aqi_days
    from {{ ref('stg_city_day') }} group by city, date_trunc('month', date)
)
select coalesce(d.city, m.city) as city, coalesce(d.month_start, m.month_start) as month_start
from daily d
full outer join {{ ref('mart_monthly_city_summary') }} m
    on d.city = m.city and d.month_start = m.month_start
where d.city is null or m.city is null
    or d.days_recorded != m.days_recorded or d.days_measured != m.days_measured
    or d.excluded_aqi_days != m.excluded_aqi_days or d.missing_aqi_days != m.missing_aqi_days
    or not equal_null(d.avg_aqi, m.avg_aqi)
    or m.days_recorded != m.days_measured + m.excluded_aqi_days + m.missing_aqi_days
    or m.unhealthy_day_share < 0 or m.unhealthy_day_share > 1
