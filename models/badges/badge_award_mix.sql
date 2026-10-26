-- Where the holders come from. A mostly backfilled badge says little yet about whether it motivates anyone.
select
    award_type,
    count(*)                         as holders,
    count(*) / sum(count(*)) over () as share_of_holders
from {{ ref('stg_badge_awards') }}
group by 1
order by 1
