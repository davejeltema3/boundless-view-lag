# What actually happened when YouTube changed how it counts views

Measurements taken 2026-08-23 to 2026-08-29 on a YouTube channel of roughly
77,800 subscribers: long-form, education niche, subscriber-heavy traffic.
Raw data and the code that produced it are in this repository.

Every figure below is either **measured**, **inferred** from those measurements,
or explicitly **not claimable**. The three are kept separate on purpose.

Full tables, source queries and a claims-to-evidence map: **[DATA.md](DATA.md)**.

> **An earlier version of this document reached the opposite conclusion.** It was
> written on 2026-08-28, when the newest available data was 2026-08-26, and it
> reported the change as a 1.2% effect. That was wrong, because the switch had not
> yet reached this channel on any of the days it examined. The correction is kept
> visible rather than quietly edited, because being wrong that way is itself one
> of the findings below. See section 4.

---

## Confirmed by measurement

### 1. The change arrived three days late, and it is large

```
day          views    engaged     gap      multiplier
2026-08-22    8,098     8,090     0.10%      1.00x
2026-08-23    8,197     8,100     1.18%      1.01x
2026-08-24    6,470     6,391     1.22%      1.01x   <- the announced date
2026-08-25    5,122     5,038     1.64%      1.02x
2026-08-26    4,971     4,924     0.95%      1.01x
2026-08-27    9,217     4,140    55.08%      2.23x   <- the actual switch
```

YouTube announced 2026-08-24. On this channel, nothing happened on that date or
for two days after. The switch landed on **2026-08-27**, and public views ran at
**2.23x**, an increase of **123%**.

### 2. The mechanism: it depends on where the video was playing

This is the finding that explains everything else.

```
playback location            pre-change    on 08-27    multiplier
BROWSE (home / subs feed)      99.82%       17.99%       5.56x
CHANNEL (channel page)         99.51%       35.14%       2.85x
WATCH (the video page)         99.93%       71.95%       1.39x
EMBEDDED (offsite players)    100.00%      100.00%       1.00x
```

**Feed views multiplied by 5.6x. Watch-page views by 1.4x. Embedded players did
not change at all.**

The same pattern by traffic source: subscriptions feed 2.78x and search 2.81x,
against suggested video 1.08x, playlists 1.07x, end screens and external links
1.00x.

### 3. Retention was not affected, and the arithmetic proves it

A reasonable fear was that retention would collapse platform-wide, since it is a
ratio with views in the denominator. It did not. Average view percentage went
**up** slightly on the switch day, 28.10 to 28.30.

On 2026-08-27 the channel logged 19,936 estimated minutes watched:

```
19,936 min / 4,140 engaged views = 289 seconds   <- matches the reported 286s
19,936 min / 9,217 public views  = 130 seconds   <- does not match
```

**YouTube computes `averageViewDuration` and `averageViewPercentage` against
engaged views, not against the inflated public count.** Anyone whose retention
appears to have crashed is looking at something else.

### 4. Reading this data early produces a wrong answer

Days keep being revised for roughly five days after they first appear:

```
2026-08-19 views   12,812 -> 12,637   (-175, -1.4%)
2026-08-21 views    8,896 ->  8,789   (-107, -1.2%)
2026-08-22 views    8,163 ->  8,098    (-65, -0.8%)
```

Measured on 2026-08-24, the pre-change days appeared to carry gaps of 0.8 to
1.4%. Settled, those same days read 0.06 to 0.26%.

This is not an abstract caution. The first version of this document was built on
data from before the switch reached this channel and concluded the effect was
around 1.2%. The real figure is 55%. **Anyone who measured this change in its
first days measured nothing.**

### 5. Engaged views arrive once a day, 44 to 48 hours behind

```
2026-08-22   appeared 08-24 20:11 UTC   44.2 hours behind
2026-08-23   appeared 08-25 21:48 UTC   45.8 hours behind
2026-08-24   appeared 08-26 20:34 UTC   44.6 hours behind
2026-08-25   appeared 08-27 23:51 UTC   47.9 hours behind
```

There is no faster source. The Analytics API has no time dimension finer than
`day`, Studio's realtime card shows views only and never engaged views, and the
bulk Reporting API is slower.

### 6. Nothing moved on the announced date

Hourly view rate on a fixed set of 47 videos, sampled every 60 seconds across
2026-08-24 through 2026-08-26: normal daily rhythm, no step change. The step
came on the 27th.

### 7. Public view counts go down as well as up

At one-minute resolution the counter was observed dropping 18 views inside a
single minute. That is the validation pass discarding low-quality playbacks,
visible only at high sampling resolution.

### 8. Two pipelines, and only one is live

Studio's realtime card updates within minutes. The Content tab, Advanced mode and
the API read a processed daily table roughly two days behind. Same platform,
different plumbing. That gap is why the switch was visible in realtime on the
27th but not confirmable until the 29th.

### 9. The in-product notice arrived days late

The Studio banner saying "we updated how views are counted, so recent counts may
be higher" appeared around 2026-08-27, three days after the announced date and
apparently the same day the change actually landed here.

---

## Reasonable inferences

Supported by the measurements, one step removed from them.

- **The inflation is autoplay previews being counted.** The surfaces that
  multiplied are the ones where a video plays automatically as you scroll past.
  The surfaces where a viewer deliberately clicks barely moved at all.

- **There is no single number for "how much will my views go up."** It depends
  entirely on traffic mix. A browse-and-search channel roughly triples. A channel
  living on suggested video, playlists and external links sees almost nothing.
  Per-video ratios on this channel span 21% to 95% on the same day.

- **A view now means materially less than it did**, on the surfaces where most
  discovery happens. Not because viewers changed, but because a scroll-past now
  counts the same as a click.

- **The rollout is staggered.** Nothing changed here on the announced date, then
  everything changed three days later. Other channels may have switched on other
  dates, which makes cross-channel comparisons over this window unreliable.

- **A rate change measured across a boundary is a lower bound.** Live-counter
  sampling on the 28th indicated +62%. The clean daily figure was +123%. The
  sampling windows straddled the switch, dragging the estimate down.

---

## Cannot be claimed from this data

- **One channel.** Long-form, education, subscriber-heavy. The mechanism should
  generalise. The magnitude depends on a channel's own traffic mix.
- **One post-change day** at full resolution.
- **No other channel's engaged views.** That data is private to each owner.
  Everything about other channels here is public view counts only.
- **No monetisation effect measured.** Earnings are based on engaged views, which
  did not change definition.
- **No explanation for the three-day delay.** The rollout order is unknown.
- **Not established as platform-wide.** Realtime graphs on other channels showed a
  similar step on the same night, but without engaged-view access that is
  suggestive, not proof.

---

## What here is new

Not in YouTube's announcement, and not in the coverage:

1. The change **did not take effect on the announced date** on this channel, and
   there is a timestamped record of the days either side.
2. The measured size: **2.23x, a 123% increase**, far above what was being
   discussed.
3. **The mechanism**, isolated by playback location: browse 5.6x against watch
   page 1.4x and embedded 1.0x.
4. **Retention was never affected**, proven by arithmetic rather than asserted.
5. Engaged views run **44 to 48 hours behind**, measured four times.
6. A **five-day revision window** that makes early measurement worthless, this
   document's own first draft being the worked example.
7. A **pre-change baseline captured 2026-08-23** and committed publicly before the
   change took effect: 110 videos, two baskets of other channels, retention
   curves and traffic splits.
