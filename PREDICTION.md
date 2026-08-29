# Two predictions, written before the data exists

Written **2026-08-28, 05:45 UTC**. At this moment the YouTube Analytics API will
only report through **2026-08-25**. The 26th, 27th and 28th do not exist in it
yet and will not for roughly two more days.

## The observation

Starting around **2026-08-27 03:21 UTC**, the live public view counter on the
measured channel began running substantially faster, with no upload and nothing
trending.

Measured from per-video cumulative counts on an identical basket of 110 videos:

```
window 1   08-26 06:20 -> 08-27 03:21   21.0 h    4,448 views    212/hr
window 2   08-27 03:21 -> 08-28 05:45   26.4 h    9,034 views    342/hr

channel-wide change in hourly view rate:   +61.7%   (1.62x)
```

Cross-check: this basket recorded 13,482 views across the 48 hours, against
14,051 on Studio's channel-level realtime card for the same period.

**The increase is broad-based, not one video trending:**

```
2.25x   5 Golden Rules of Game Cards Graphic Design   (published Sep 2023)
2.17x   How to Survive Being a Small YouTube Channel  (Mar 2025)
2.08x   8 Things You Should NEVER Do AFTER Uploading  (Jul 2025)
1.92x   10 Steps to ACTUALLY Design a Board Game      (Aug 2023)
1.53x   I Uploaded to YouTube Once a Week for a Year  (Dec 2025)

20 videos measured, median 1.45x, 12 up more than 25%, 2 down
```

A board game video from 2023 does not organically double in the same hour as
everything else. That is the signature of a counting change, not of traffic.

## Prediction A (the conservative one)

The 2026-08-24 switch landed as announced and its effect is small. Days 08-26
through 08-28 will come in with an engaged-views gap of **1.5% to 2.5%**, in line
with the 1.22% and 1.64% already recorded for the 24th and 25th. What the live
counter is showing is a genuine traffic surge.

## Prediction B (the one the evidence now favours)

The public-view switch did not actually take effect on this channel until roughly
**2026-08-27 03:21 UTC**, three days after the announced date. When 08-27 and
08-28 land in Analytics they will show an engaged-views gap of roughly **31% to
38%**, while 08-24 through 08-26 stay near 1.5%.

The 31 to 38 percent range is derived from the observed rate change: a 1.45x
median implies a 31% gap, a 1.62x channel-wide figure implies 38%.

## How to check

Query the Analytics API for `views` and `engagedViews` by day once 2026-08-27
becomes available, expected around 2026-08-29 or 08-30 given the observed 44 to
48 hour lag. Compare the gap on the 27th and 28th against the gap on the 24th
through 26th.

Note that days keep being revised for about five days after they first appear,
by more than 1% in observed cases, so the first read is not final.

## What would make each one wrong

- **A is wrong** if the gap on 08-27 and 08-28 comes in above about 10%.
- **B is wrong** if those days come in below about 10%, which would mean the live
  surge was traffic and the counting change really was small.

Both cannot be true. This resolves itself in about two days.
