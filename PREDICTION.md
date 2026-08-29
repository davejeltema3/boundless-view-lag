# Two predictions, and the result

**Predictions written 2026-08-28 05:45 UTC. Result recorded 2026-08-29 21:00 UTC.**

At the time the predictions were written, the YouTube Analytics API would only
report through 2026-08-25. The 26th and 27th did not exist in it yet.

---

## RESULT: Prediction B was right about the date, and both predictions
## underestimated the size

```
day          views    engaged     gap      multiplier
2026-08-24    6,470     6,391     1.22%      1.01x
2026-08-25    5,122     5,038     1.64%      1.02x
2026-08-26    4,971     4,924     0.95%      1.01x
2026-08-27    9,217     4,140    55.08%      2.23x     <-- the switch
```

The counting change did **not** take effect on this channel on 2026-08-24, the
date YouTube announced. The days on either side of that date carry gaps of about
1%, which is the noise floor. **The switch landed on 2026-08-27**, three days
late, and public views on that day ran at **2.23x**, an increase of **123%**.

- **Prediction A** (the conservative one: change landed on the 24th, gap settles
  at 1.5 to 2.5%) is **wrong**.
- **Prediction B** (the switch landed 2026-08-27, gap of 31 to 38%) is **right
  about the date and low on the magnitude**. Actual: 55.08%.

The 31 to 38% range was derived from a live-counter rate change measured across
imperfect window boundaries. The true effect was larger than that measurement
suggested.

---

## What the predictions said

**Prediction A.** The 2026-08-24 switch landed as announced and its effect is
small. Days 08-26 through 08-28 come in at a 1.5% to 2.5% gap. What the live
counter showed was a genuine traffic surge.

**Prediction B.** The public-view switch did not take effect on this channel
until roughly 2026-08-27 03:21 UTC. When 08-27 and 08-28 land in Analytics they
show a gap of roughly 31 to 38%, while 08-24 through 08-26 stay near 1.5%.

## The observation the predictions were built on

Measured from per-video cumulative counts on an identical basket of 110 videos:

```
window 1   08-26 06:20 -> 08-27 03:21   21.0 h    4,448 views    212/hr
window 2   08-27 03:21 -> 08-28 05:45   26.4 h    9,034 views    342/hr
                                        channel-wide  +61.7%   (1.62x)
```

Cross-checked against Studio's channel realtime card: 13,482 in this basket
against 14,051 channel-wide over the same 48 hours.

The increase was broad-based rather than one video trending. Median 1.45x across
20 videos, 12 up more than 25%, including videos published in 2023 that doubled
in the same hour as everything else.

## Why the live measurement understated it

The live-counter windows straddled the switch. Window 2 began at 03:21 UTC on the
27th but the switch appears to have taken effect around 00:00 to 04:00 UTC, so
part of window 2 was still being counted the old way. That drags the measured
rate change below the true one. The daily figure, measured cleanly over a full
day, is the accurate one.

The lesson generalises: **a rate change measured across a boundary is a lower
bound, not an estimate.**

## Notes for anyone checking this

Days keep being revised for roughly five days after they first appear.
2026-08-24 first appeared with a 1.22% gap and later settled at 1.22% after
intermediate readings as high as 1.4%. Treat any single read as provisional.

All figures above are reproducible from `data/` in this repository, and the
commit history shows the predictions were recorded before the data existed.
