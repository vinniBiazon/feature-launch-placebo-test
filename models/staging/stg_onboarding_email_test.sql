select
    member_id,
    cast(signed_up_on as date)        as signed_up_on,
    variant,
    cast(first_workout_7d as integer) as first_workout_7d,
    cast(active_day_30 as integer)    as active_day_30
from {{ source('raw', 'onboarding_email_test') }}
