# Every number, where it came from, and what it proves

Measured on one YouTube channel (~77,800 subscribers, long-form, education
niche) across the 2026-08-24 view-counting change. Every figure here is
reproducible from `data/` in this repository or from the query noted beside it.

Channel state at capture: **3,945,693 lifetime views, 77,800 subscribers,
100 public videos.**

Last day available in Analytics at time of writing: **2026-08-27**
(lag of roughly 45 hours).

---

## 1. The headline: daily views vs engaged views

Chart this as two lines, or as a bar with a gap band.

| day | views | engaged | gap % | multiplier | avg view % | avg duration (s) |
|---|---|---|---|---|---|---|
| 2026-08-13 | 5,519 | 5,463 | 1.01 | 1.01x | 27.57 | 249 |
| 2026-08-14 | 5,635 | 5,634 | 0.02 | 1.00x | 27.31 | 236 |
| 2026-08-15 | 5,264 | 5,256 | 0.15 | 1.00x | 26.99 | 236 |
| 2026-08-16 | 5,703 | 5,698 | 0.09 | 1.00x | 27.58 | 246 |
| 2026-08-17 | 6,474 | 6,460 | 0.22 | 1.00x | 25.69 | 276 |
| 2026-08-18 | 5,790 | 5,780 | 0.17 | 1.00x | 22.46 | 269 |
| 2026-08-19 | 12,637 | 12,626 | 0.09 | 1.00x | 28.45 | 353 |
| 2026-08-20 | 7,035 | 7,031 | 0.06 | 1.00x | 24.20 | 295 |
| 2026-08-21 | 8,789 | 8,784 | 0.06 | 1.00x | 17.94 | 212 |
| 2026-08-22 | 8,098 | 8,090 | 0.10 | 1.00x | 18.00 | 205 |
| 2026-08-23 | 8,197 | 8,100 | 1.18 | 1.01x | 18.03 | 203 |
| **2026-08-24** | 6,470 | 6,391 | 1.22 | 1.01x | 22.16 | 246 |
| 2026-08-25 | 5,122 | 5,038 | 1.64 | 1.02x | 25.78 | 275 |
| 2026-08-26 | 4,971 | 4,924 | 0.95 | 1.01x | 28.10 | 297 |
| **2026-08-27** | **9,217** | **4,140** | **55.08** | **2.23x** | 28.30 | 286 |

**The claim this supports:** YouTube announced 2026-08-24. On this channel the
change took effect **2026-08-27**, three days late, and multiplied public views
by **2.23x (+123%)**.

Caveat to state: days before 2026-08-13 carry gaps of 4 to 9%, which is Shorts
traffic mixed in, not long-form. The clean pre-change baseline is 08-13 to 08-26.

*Query: `metrics=views,engagedViews,averageViewPercentage,averageViewDuration`,
`dimensions=day`.*

---

## 2. The mechanism: where the video was playing

This is the strongest cut in the whole dataset. Chart as paired bars, before and
after.

| playback location | pre-change ratio | on 08-27 | multiplier |
|---|---|---|---|
| **BROWSE** (home and subscriptions feed) | 99.82% | **17.99%** | **5.56x** |
| WATCH (the video page) | 99.93% | 71.95% | 1.39x |
| CHANNEL (channel page) | 99.51% | 35.14% | 2.85x |
| EMBEDDED (offsite players) | 100.00% | 100.00% | 1.00x |

Raw counts: BROWSE pre 18,437 views / 18,403 engaged. BROWSE post 4,598 views /
827 engaged.

**The claim this supports:** the inflation is not spread evenly. **Feed views
multiplied by 5.6x. Watch-page views multiplied by 1.4x. Embedded players did not
change at all.** Those are the surfaces where a video auto-previews as you scroll.
Those previews now count as views.

*Query: `dimensions=insightPlaybackLocationType`, pre = 08-14 to 08-26, post = 08-27.*

---

## 3. The same mechanism by traffic source

| traffic source | pre-change | on 08-27 | multiplier |
|---|---|---|---|
| SUBSCRIBER (subscriptions feed) | 99.90% | 36.00% | 2.78x |
| YT_SEARCH | 99.71% | 35.62% | 2.81x |
| YT_CHANNEL | 98.18% | 58.78% | 1.70x |
| YT_OTHER_PAGE | 99.81% | 86.36% | 1.16x |
| RELATED_VIDEO (suggested) | 99.93% | 92.76% | 1.08x |
| NO_LINK_OTHER | 99.46% | 95.33% | 1.05x |
| PLAYLIST | 99.65% | 93.75% | 1.07x |
| EXT_URL (external links) | 100.00% | 100.00% | 1.00x |
| END_SCREEN | 100.00% | 100.00% | 1.00x |

**The claim this supports:** how much a channel's views inflate depends entirely
on its traffic mix. **A feed-and-search channel roughly triples. A suggested-video
or playlist channel barely moves. "Everyone gets 60% more views" is wrong.**

*Query: `dimensions=insightTrafficSourceType`.*

---

## 4. By device

| device | pre-change | on 08-27 | multiplier |
|---|---|---|---|
| MOBILE | 99.75% | 41.67% | 2.40x |
| DESKTOP | 99.86% | 40.27% | 2.48x |
| TV | 99.99% | 69.39% | 1.44x |
| TABLET | 99.97% | 96.18% | 1.04x |

Mobile and desktop are hit almost identically. TV much less. Tablet barely at all.

*Query: `dimensions=deviceType`.*

---

## 5. By subscriber status

| viewer | pre-change | on 08-27 | multiplier |
|---|---|---|---|
| UNSUBSCRIBED | 99.84% | 43.82% | 2.28x |
| SUBSCRIBED | 99.61% | 63.83% | 1.57x |

Note the distinction from section 3: the **SUBSCRIBER traffic source** is the
subscriptions feed, a browse surface, and it inflated 2.78x. **SUBSCRIBED
viewers** as people inflated only 1.57x. Different dimensions, not a contradiction.

*Query: `dimensions=subscribedStatus`.*

---

## 6. Retention did not collapse, and here is the proof

A reasonable fear was that retention would fall platform-wide, since it is a
ratio with views in the denominator. It did not.

```
2026-08-26   avg view %  28.10    avg duration 297s
2026-08-27   avg view %  28.30    avg duration 286s
```

The arithmetic shows why. On 2026-08-27 the channel logged **19,936 estimated
minutes watched**.

```
19,936 min / 4,140 engaged views = 4.82 min = 289 seconds   <- matches the reported 286s
19,936 min / 9,217 public views  = 2.16 min = 130 seconds   <- does not match
```

**The claim this supports:** YouTube computes `averageViewDuration` and
`averageViewPercentage` against **engaged views**, not against the inflated public
count. Retention metrics were not touched by this change. Anyone claiming their
retention crashed because of the view change is looking at something else.

*Query: `metrics=estimatedMinutesWatched,averageViewDuration,averageViewPercentage`, `dimensions=day`.*

---

## 7. Per-video spread on the switch day

The channel-wide 2.23x hides enormous variance between videos. Chart as a
histogram or a sorted bar.

| video | published | duration | views | engaged | ratio |
|---|---|---|---|---|---|
| Everyone Gets Thumbnails Wrong... | 2026-01-20 | 21:04 | 28 | 6 | 21.4% |
| How Small Creators Win YouTube's NEW Algorithm | 2025-09-10 | 9:51 | 48 | 12 | 25.0% |
| Every bad board game designer does this. | 2023-09-05 | 6:49 | 101 | 34 | 33.7% |
| 8 Things You Should NEVER Do AFTER Uploading | 2025-07-15 | 7:38 | 3,083 | 1,204 | 39.1% |
| How to Survive Being a Small YouTube Channel | 2025-03-18 | 6:03 | 722 | 285 | 39.5% |
| 5 Golden Rules of Game Cards Graphic Design | 2023-09-24 | 11:27 | 281 | 112 | 39.9% |
| I Uploaded to YouTube Once a Week for a Year | 2025-12-18 | 33:03 | 2,091 | 933 | 44.6% |
| YouTube's New Update Just Changed Everything | 2026-08-19 | 21:41 | 782 | 370 | 47.3% |
| 12 Things you MUST do AFTER Uploading | 2025-03-05 | 12:43 | 481 | 256 | 53.2% |
| How Much I Make On YouTube With 50k Subscribers | 2026-01-12 | 22:44 | 130 | 74 | 56.9% |
| It Took Me 1,000+ Hours to Figure Out YouTube | 2025-07-02 | 41:14 | 60 | 47 | 78.3% |
| The Real Reason Some Channels Take Off | 2026-07-25 | 19:21 | 40 | 38 | 95.0% |

Range: **21.4% to 95.0%**. Thirty videos measured.

**The claim this supports:** there is no single number for "your videos." A video
fed to browse inflates far more than one people seek out. Small-sample videos at
the bottom of the list are noisy and should be labelled as such.

*Query: `dimensions=video`, `sort=-views`, filtered to 2026-08-27.*

---

## 8. The reporting lag, measured four times

| day of data | first appeared | hours behind |
|---|---|---|
| 2026-08-22 | 2026-08-24 20:11 UTC | 44.2 |
| 2026-08-23 | 2026-08-25 21:48 UTC | 45.8 |
| 2026-08-24 | 2026-08-26 20:34 UTC | 44.6 |
| 2026-08-25 | 2026-08-27 23:51 UTC | 47.9 |

**The claim this supports:** engaged views arrive **once a day, 44 to 48 hours
behind**. There is no faster source. The Analytics API has no dimension finer
than `day`, Studio's realtime card shows views only and never engaged views, and
the bulk Reporting API is slower.

*Source: `data/changes.jsonl`, NEW DAY events.*

---

## 9. The five-day revision window

Days keep changing after they first appear.

```
2026-08-19 views   12,812 -> 12,637   (-175, -1.4%)
2026-08-21 views    8,896 ->  8,789   (-107, -1.2%)
2026-08-22 views    8,163 ->  8,098    (-65, -0.8%)
```

Measured on 2026-08-24, the pre-change days appeared to carry gaps of 0.8 to
1.4%. Once settled, those same days read 0.06 to 0.26%.

**The claim this supports:** **reading this data early produces a wrong answer.**
Anyone who measured the change in its first days measured unsettled numbers. A
single read is never final.

*Source: `data/changes.jsonl`, REVISED events.*

---

## 10. The public counter never jumped on the announced date

Hourly view rate on a fixed set of 47 videos, sampled every 60 seconds:

```
08-24 09h  180/hr    08-25 09h  149/hr    08-26 09h  180/hr
08-24 13h  300/hr    08-25 13h  330/hr    08-26 13h  240/hr
08-24 19h  660/hr    08-25 19h  240/hr    08-26 19h  240/hr
08-24 23h  360/hr    08-25 23h  238/hr    08-26 23h  240/hr
```

Normal daily rhythm through the announced date. The step change came on the 27th.

*Source: `data/ticks.csv`.*

---

## 11. Shorts, for contrast

Shorts moved to first-frame counting in 2025, a year before long-form.

```
pre-change long-form sources     97.7% to 100.0% engaged
SHORTS traffic source            47.1% engaged  (small sample, 17 views)
one Short, 28-day window         2,148 views / 707 engaged = 32.9% engaged
```

**The claim this supports:** anyone quoting a huge gap before 2026-08-27 was
quoting their Shorts. The two formats were never comparable.

---

## 12. The pre-change baselines that cannot be recreated

YouTube's developer notice states the pre-switch public view count "will no
longer be accessible via the YouTube Public Data API."

| capture | contents | file |
|---|---|---|
| own catalogue | 110 videos, public counters, lifetime views vs engaged, retention curves, traffic and device splits | `data/catalog_pre.json` |
| reference basket | 21 channels, 4,140 to 789,000 subs, 1,878 videos, 588,558,353 combined views | `data/basket_pre.json` |
| second basket | 30 channels anonymised, 40 to 14,100 subs, 1,794 videos | `data/basket_clients_anon.json` |

All captured 2026-08-23, committed before the change took effect.

---

## Claims-to-evidence map

| claim you might make | evidence | strength |
|---|---|---|
| The change landed 3 days late on this channel | Section 1 | Strong, one channel |
| Public views multiplied 2.23x | Section 1 | Strong, one channel, one day |
| Feed views multiplied 5.6x, watch page 1.4x | Section 2 | Strong, the mechanism |
| Your inflation depends on your traffic mix | Sections 2, 3, 7 | Strong |
| Retention was NOT affected | Section 6 | Strong, arithmetic proof |
| Engaged views run 44 to 48 hours behind | Section 8 | Strong, 4 observations |
| Numbers keep revising for ~5 days | Section 9 | Strong |
| Nothing visibly changed on the announced date | Sections 1, 10 | Strong |
| Big gaps before 08-27 were Shorts | Section 11 | Moderate, small sample |
| This is happening platform-wide | not yet measured | **Weak. Do not claim.** |

## What is not measured here

- **One primary channel.** Long-form, subscriber-heavy, education niche.
- **One post-change day** at full resolution. 08-28 onward had not landed.
- **No other channel's engaged views.** That data is private to each owner.
  Everything about other channels in this repo is public view counts only.
- **No monetisation effect.** Earnings are based on engaged views, which did not
  change definition, but no revenue impact was measured.
- **No claim about the rollout order.** Why this channel switched on the 27th
  rather than the 24th is unknown.
