select
    member_id,
    badge,
    cast(awarded_on as date) as awarded_on,
    award_type               -- backfill: already past the threshold at launch; organic: earned after launch
from {{ source('raw', 'badge_awards') }}
