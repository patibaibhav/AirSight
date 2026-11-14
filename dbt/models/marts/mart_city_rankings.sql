with periods as (
    select city, 'overall' as period_scope, cast(null as integer) as year,
        avg(aqi) as avg_aqi, count(*) as days_recorded, count(aqi) as days_measured,
        count_if(aqi_out_of_range) as excluded_aqi_days,
        100.0 * count_if(aqi is not null and aqi_bucket in ('Poor', 'Very Poor', 'Severe'))
            / nullif(count(aqi), 0) as pct_unhealthy_days
    from {{ ref('stg_city_day') }} group by city
    union all
    select city, 'yearly' as period_scope, year,
        avg(aqi) as avg_aqi, count(*) as days_recorded, count(aqi) as days_measured,
        count_if(aqi_out_of_range) as excluded_aqi_days,
        100.0 * count_if(aqi is not null and aqi_bucket in ('Poor', 'Very Poor', 'Severe'))
            / nullif(count(aqi), 0) as pct_unhealthy_days
    from {{ ref('stg_city_day') }} group by city, year
), monthly_periods as (
    select city, 'overall' as period_scope, cast(null as integer) as year, month_start, avg_aqi
    from {{ ref('mart_monthly_city_summary') }} where avg_aqi is not null
    union all
    select city, 'yearly' as period_scope, year(month_start) as year, month_start, avg_aqi
    from {{ ref('mart_monthly_city_summary') }} where avg_aqi is not null
), best as (
    select city, period_scope, year, month_start from monthly_periods
    qualify row_number() over (
        partition by city, period_scope, year order by avg_aqi asc, month_start asc
    ) = 1
), worst as (
    select city, period_scope, year, month_start from monthly_periods
    qualify row_number() over (
        partition by city, period_scope, year order by avg_aqi desc, month_start asc
    ) = 1
)
select
    p.city || '|' || p.period_scope || '|' || coalesce(to_varchar(p.year), 'ALL') as ranking_key,
    p.city, p.period_scope, p.year, p.avg_aqi,
    case when p.avg_aqi is not null then dense_rank() over (
        partition by p.period_scope, p.year order by p.avg_aqi desc nulls last
    ) end as pollution_rank,
    p.days_recorded, p.days_measured, p.excluded_aqi_days, p.pct_unhealthy_days,
    b.month_start as best_month, w.month_start as worst_month
from periods p
left join best b on p.city = b.city and p.period_scope = b.period_scope and equal_null(p.year, b.year)
left join worst w on p.city = w.city and p.period_scope = w.period_scope and equal_null(p.year, w.year)
