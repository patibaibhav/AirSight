with bounds as (
    select city, min(month_start) as first_month, max(month_start) as last_month
    from {{ ref('mart_monthly_city_summary') }} group by city
), offsets as (
    select row_number() over (order by seq4()) - 1 as month_offset
    from table(generator(rowcount => 1200))
), calendar as (
    select b.city, dateadd('month', o.month_offset, b.first_month)::date as month_start
    from bounds b cross join offsets o
    where dateadd('month', o.month_offset, b.first_month) <= b.last_month
), monthly as (
    select c.city, c.month_start, m.avg_aqi, coalesce(m.days_measured, 0) as days_measured
    from calendar c
    left join {{ ref('mart_monthly_city_summary') }} m
        on c.city = m.city and c.month_start = m.month_start
), rolling as (
    select city, month_start, avg_aqi, days_measured,
        avg(avg_aqi) over (
            partition by city order by month_start rows between 2 preceding and current row
        ) as rolling_3_month_avg,
        count(avg_aqi) over (
            partition by city order by month_start rows between 2 preceding and current row
        ) as rolling_months_measured
    from monthly
)
select
    this_month.city || '|' || to_char(this_month.month_start, 'YYYY-MM-DD') as city_month_key,
    this_month.city, this_month.month_start,
    year(this_month.month_start) as year, month(this_month.month_start) as month,
    this_month.avg_aqi, this_month.days_measured,
    this_month.rolling_3_month_avg, this_month.rolling_months_measured,
    previous_year.avg_aqi as prior_year_avg_aqi,
    this_month.avg_aqi - previous_year.avg_aqi as yoy_change,
    100.0 * (this_month.avg_aqi - previous_year.avg_aqi) / nullif(previous_year.avg_aqi, 0) as yoy_change_pct,
    case
        when month(this_month.month_start) in (12, 1, 2) then 'Winter'
        when month(this_month.month_start) in (3, 4, 5) then 'Pre-monsoon'
        when month(this_month.month_start) in (6, 7, 8, 9) then 'Monsoon'
        else 'Post-monsoon'
    end as season
from rolling this_month
left join monthly previous_year
    on this_month.city = previous_year.city
    and previous_year.month_start = dateadd('year', -1, this_month.month_start)
