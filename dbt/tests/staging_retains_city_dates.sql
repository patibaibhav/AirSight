with raw_keys as (
    select distinct upper(trim(to_varchar("City"))) as city,
        try_to_date(to_varchar("Date")) as date
    from {{ source('air_quality', 'city_day') }}
)
select r.city, r.date
from raw_keys r
full outer join {{ ref('stg_city_day') }} s on r.city = s.city and r.date = s.date
where r.city is null or s.city is null or r.date is null or s.date is null
