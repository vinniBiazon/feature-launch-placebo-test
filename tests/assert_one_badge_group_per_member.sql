select member_id, count(*) as n
from {{ ref('badge_groups') }}
group by 1
having count(*) > 1
