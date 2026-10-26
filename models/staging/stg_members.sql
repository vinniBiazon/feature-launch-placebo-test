select
    member_id,
    cast(joined_on as date)             as joined_on,
    cast(workouts_before_2024 as integer) as workouts_before_2024
from {{ source('raw', 'members') }}
