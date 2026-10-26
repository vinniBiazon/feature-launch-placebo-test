-- Before and after windows must cover the same number of days, or the comparison is not like for like
select *
from {{ ref('feed_scenarios') }}
where (split_date - before_start) != (after_end - split_date + 1)
