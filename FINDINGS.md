# What actually happened when YouTube changed how it counts views

Measurements from the Boundless view-lag probe, 2026-08-23 to 2026-08-28.
Channel: Dave Jeltema, ~77,500 subscribers, long-form heavy, subscriber-heavy.

Everything below is either **measured** on this channel, **inferred** from those
measurements, or explicitly **not claimable**. The three are kept separate on
purpose.

---

## Confirmed by measurement

### 1. The gap opened, but it is small

Engaged views as a share of views, by day:

```
PRE-CHANGE                      POST-CHANGE
2026-08-19    0.09% gap         2026-08-24    1.22% gap
2026-08-20    0.06% gap         2026-08-25    1.64% gap
2026-08-21    0.06% gap
2026-08-22    0.10% gap
2026-08-23    0.26% gap
```

Before the change, views and engaged views were the same number to within a
tenth of a percent. After, the gap is roughly **1.2 to 1.6 percent**.

So the effect is real and detectable, about **ten to twenty times larger** than
the pre-change noise floor. It is also, in absolute terms, tiny. Out of every
100 views, roughly 99 still count as engaged.

### 2. Shorts and long-form are completely different stories

Same channel, same window:

```
long-form   11,501 views   11,366 engaged    1.17% gap
Shorts      one video: 2,148 views, 707 engaged   67.1% gap
```

Shorts have been counted this way since 2025. Long-form just joined them, and
barely moved. The two formats are not remotely comparable.

### 3. Engaged views arrive once a day, about two days late

Every observed first appearance of a new day of data:

```
2026-08-22   appeared 08-24 20:11 UTC   44.2 hours behind
2026-08-23   appeared 08-25 21:48 UTC   45.8 hours behind
2026-08-24   appeared 08-26 20:34 UTC   44.6 hours behind
2026-08-25   appeared 08-27 23:51 UTC   47.9 hours behind
```

Once per day, consistently 44 to 48 hours after the day ends. There is no faster
source: the API has no time dimension finer than `day`, Studio's realtime card
shows views only and never engaged views, and the bulk Reporting API is slower.

### 4. Numbers keep changing for about five days after they land

Revisions the probe caught, on days that had already been reported:

```
2026-08-19 views  12,812 -> 12,637   (-175)
2026-08-21 views   8,896 ->  8,789   (-107)
2026-08-22 views   8,163 ->  8,098    (-65)
```

This matters more than it sounds. On 2026-08-24 the pre-change days appeared to
have gaps of 0.8 to 1.4 percent. Once they settled, those same days read 0.06 to
0.26 percent. **Reading the data early produced a wrong answer about the size of
the change.** Anyone who measured this in the first days measured noise.

### 5. The public view counter did not visibly jump

Hourly view rate across the switch, sampled every 60 seconds on a fixed set of
50 videos:

```
08-24 09h  180/hr      08-25 09h  149/hr      08-26 09h  180/hr
08-24 13h  300/hr      08-25 13h  330/hr      08-26 13h  240/hr
08-24 19h  660/hr      08-25 19h  240/hr      08-26 19h  240/hr
08-24 23h  360/hr      08-25 23h  238/hr      08-26 23h  240/hr
```

Normal daily rhythm, no step change. Whatever inflation happened was inside the
1.4 percent, not a visible jump.

### 6. Public view counts go down as well as up

At one-minute resolution the counter was observed dropping:

```
19:34:56   3,430,832 -> 3,430,814   (-18 in under a minute)
```

That is YouTube's validation pass discarding low-quality playbacks in near real
time. Invisible at normal resolution.

### 7. Two pipelines, and only one is live

The Studio dashboard's realtime card updates within minutes. The Content tab and
Advanced mode read a processed daily table that runs about two days behind. Same
platform, different plumbing. This is why the public number and the analytics
number disagree at any given moment, and it is not a bug.

### 8. Retention did not collapse

A reasonable fear was that retention, being a ratio with views in the
denominator, would fall platform-wide the moment views inflated. Average view
percentage on this channel:

```
pre    17.94  18.00  18.03
post   22.16  25.78
```

It went up, not down. No evidence of a retention recompute here.

### 9. YouTube's in-product notice arrived days late

The change took effect 2026-08-24. The banner in Studio saying "we updated how
views are counted, so recent counts may be higher" appeared around 2026-08-27.
Creators had three days of changed numbers before being told in the product.

---

## Reasonable inferences

Supported by the measurements, but one step removed from them.

- **The engaged threshold for long-form is very short.** If roughly 99 percent
  of long-form views clear it, it cannot be anywhere near 30 seconds. YouTube
  has only ever said "some amount of seconds." A few seconds fits the data.

- **The threshold was never the point. The act is.** Clicking a thumbnail is
  deliberate. Being fed a Short and swiping is not. That difference, not the
  number of seconds, is what makes the Shorts gap 67 percent and the long-form
  gap 1 percent.

- **Most long-form channels will not see their numbers meaningfully inflate.**
  If a channel's traffic is people choosing to click, its gap should look like
  this one.

- **Shorts-heavy channels are a different case entirely**, and any channel
  reporting a big gap is probably reporting its Shorts.

- **"Your views are worth less now" is wrong for long-form.** A 1.4 percent
  shift does not change what a view means.

- **Any before-and-after comparison made inside about five days is unreliable**,
  because the underlying numbers are still settling.

---

## Cannot be claimed from this data

State these as limits, not hedges.

- **This is one channel.** Long-form, subscriber-heavy, education niche. A
  browse-heavy or Shorts-heavy channel could look very different.
- **The exact threshold in seconds is unknown.** The data bounds it as "short,"
  not as a number.
- **Two post-change days only**, and both are still inside the revision window,
  so even 1.22 and 1.64 percent may move.
- **Nothing about monetisation.** Earnings are based on engaged views, which did
  not change definition, but no revenue effect was measured here.
- **Nothing about other channels' engaged views.** That data is private to each
  channel owner and cannot be obtained without their access.
- **No claim about the future.** YouTube can tune the threshold whenever it
  wants, and this measurement would not see it coming.

---

## What here is actually new

Not in YouTube's announcement, and not in the coverage:

1. The measured size of the effect on a real channel: **0.1% to 1.4%**.
2. The engaged-view lag: **once a day, 44 to 48 hours**, measured four times.
3. The **five-day revision window**, and the fact that reading early gives a
   wrong answer.
4. The public counter showed **no step change** at the switch.
5. **Retention did not drop**, contrary to a reasonable prediction.
6. The Shorts versus long-form contrast, **quantified on one channel**: 67
   percent against 1 percent.
7. All of it sits on a **pre-change baseline captured on 2026-08-23**, committed
   to a public repository before the change took effect: 110 videos, 21
   competitor channels, 30 client channels, retention curves and traffic splits.

That last one is the part that cannot be reproduced after the fact. Anyone can
describe the change now. Almost nobody can show what the numbers looked like the
day before, with commit timestamps to prove it.

---

*Raw data, code and commit history: this repository.*
