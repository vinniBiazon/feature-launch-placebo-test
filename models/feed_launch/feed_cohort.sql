-- A fixed cohort: members who had joined before the earliest window opens.
-- The same people are measured in every window, so changes are not driven by who joined.
select m.member_id
from {{ ref('stg_members') }} m
where m.joined_on < (select min(before_start) from {{ ref('feed_scenarios') }})
