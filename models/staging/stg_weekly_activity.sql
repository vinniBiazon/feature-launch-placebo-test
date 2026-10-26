-- One row per member and week with any activity. Weeks without a row mean zero activity.
select
    member_id,
    cast(week_start as date)               as week_start,
    cast(sessions as integer)              as sessions,
    cast(workouts_logged as integer)       as workouts_logged,
    cast(kudos_given as integer)           as kudos_given,
    cast(partner_challenge_views as integer) as partner_challenge_views
from {{ source('raw', 'weekly_activity') }}
