# A prediction made before the data existed

Written 2026-08-28, roughly 05:30 UTC.

At this moment the YouTube Analytics API will only report through **2026-08-25**.
The 26th does not exist in it yet and will not for another day or so.

But the probe has been sampling the live public view counter every 60 seconds on
a fixed set of 47 videos, with 100% coverage of 2026-08-26. Over that day those
videos gained **4,702 views** on the live counter.

## The claim

When 2026-08-26 lands in the Analytics API, its `views` figure for those same 47
videos will be **within about 1% of 4,702**.

## Why this is worth stating in advance

It tests whether the live public counter and the delayed analytics table are
measuring the same thing, or whether the live pipeline is quietly counting more
and the analytics table is lagging behind it.

It has already been checked once, on the only prior day with both full probe
coverage and available analytics:

```
2026-08-25    live counter growth   4,874
              analytics views       4,873
              difference            +0.0%
```

If the prediction holds, then the two-day delay is a reporting delay and nothing
more. The number you see live is the number you will eventually see in Advanced
mode. Nothing is hiding.

If it fails, and analytics comes in materially lower, then the live counter is
inflated relative to what analytics will admit, and the size of the 2026-08-24
counting change has been understated by everyone measuring it from analytics.

## How to check it

Query the Analytics API for `views` with `dimensions=day` and
`filters=video==<the 47 ids>` for 2026-08-26. Compare to 4,702. The video ids are
derivable from `data/state.json` using `tick_ids()` in `poll.py`: the 35 newest
uploads plus the 15 most-viewed, deduplicated.

Note that the answer may drift for several days afterwards. Revisions of over 1%
have been observed on days that had already been reported, so the first read is
not final.
