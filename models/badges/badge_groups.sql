-- Holders: got the badge by the start of the "after" window (backfill at launch, or earned soon after).
-- Non-holders: did not have it at that date. Status is fixed at the start of the window and never
-- updated with what happens later: choosing groups with information from the "after" window
-- (for example dropping members who earn it mid-window) would bias the comparison.
-- Both groups joined before the "before" window and were active in the 4 weeks before launch.
-- That check uses weeks outside both measurement windows, so it does not filter on the outcome,
-- and it keeps members who had already left out of the non-holder group (holders are active by construction).
with awards as (
    select member_id, awarded_on, award_type
    from {{ ref('stg_badge_awards') }}
    where badge = 'century'
),
active_before_launch as (
    select distinct member_id
    from {{ ref('stg_weekly_activity') }}
    where week_start between date '{{ var("badge_launch") }}' - 28 and date '{{ var("badge_launch") }}' - 1
)
select
    m.member_id,
    case when a.awarded_on <= date '{{ var("badge_after_start") }}' then 'holder' else 'non_holder' end as badge_group,
    a.award_type
from {{ ref('stg_members') }} m
join active_before_launch using (member_id)
left join awards a using (member_id)
where m.joined_on < date '{{ var("badge_before_start") }}'
