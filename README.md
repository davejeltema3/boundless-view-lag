# boundless-view-lag

Two jobs, one poller.

**1. Measure the lag.** How often does the YouTube Analytics API refresh
`engagedViews`, and how far behind real time does it run? Answered by
timestamping the exact moment each new day becomes queryable.

**2. Capture the switch.** On 2026-08-24 YouTube started counting a view from the
first frame on long-form and live, and the old methodology survives as
`engagedViews` in Analytics only. YouTube's own developer notice says the
pre-switch public count "will no longer be accessible via the YouTube Public Data
API" afterwards. Everything the Data API records here is therefore unrepeatable.

## What runs, every 5 minutes

1. Refresh an OAuth access token. Analytics is private channel data, so this
   needs the channel owner's refresh token. An API key cannot reach it.
2. **Public counters for the entire catalog**, all 110 videos, not a sample.
   Views, likes, comments. Three `videos.list` calls plus a playlist walk.
3. Analytics day series at channel level: `views`, `engagedViews`,
   `estimatedMinutesWatched`, `averageViewDuration`, `averageViewPercentage`.
4. Analytics `day x video` for the 20 tracked videos, in a single call.
5. Analytics `day x insightTrafficSourceType`.
6. On a new-day event only, 100-bucket retention curves for all 20 tracked videos.

Quota: about 7 Data API units per run, roughly 2,000 a day against the 10,000
budget. The Analytics API is metered separately, so none of this competes with a
future title updater.

## What it watches for

- **NEW DAY** — a day that wasn't queryable before now is. The `lag_hours` on that
  alert is the actual measurement this repo exists for.
- **REVISED** — a day already reported changed value, including
  `averageViewPercentage`. Tells us whether numbers keep settling after landing.
- **RATE JUMP** — catalog-wide views per hour running more than 1.75x the trailing
  median. This is the tripwire for the counting switch itself, which should look
  like a step change in the public counter.

Alerts post through Hazel's own webhook into `#dashboard`, styled like the
payment alerts, colour-coded by event. That webhook is shared with
`bcp-program`'s `DISCORD_WEBHOOK_URL`, so regenerating it in Discord breaks both.

## Files

| File | What it holds |
|---|---|
| `data/pulse.csv` | one row per run: timestamp, catalog views, subs, latest day, lag |
| `data/snapshots.jsonl` | full snapshot, written hourly or on any change |
| `data/changes.jsonl` | only the runs where something moved |
| `data/retention.jsonl` | 100-bucket retention curves, captured on new-day events |
| `data/catalog_pre.json` | the pre-switch capture. See below. |
| `data/state.json` | last snapshot, for diffing |

`pulse.csv` exists because full snapshots are ~9KB and 5-minute cadence would put
2.6MB a day into git. The pulse row is what the rate analysis needs, so it goes
down every run while the heavy record lands hourly.

## The pre/post capture

`capture_baseline.py` takes the deep snapshot that only makes sense at two moments.

```
LABEL=pre  python3 capture_baseline.py     # run before 2026-08-24
LABEL=post python3 capture_baseline.py     # run after the switch has settled
```

It records every video's public counters, lifetime `views` vs `engagedViews` per
video, 100-bucket retention curves for the top 20, and views/engagedViews split
by traffic source, device and subscriber status, both lifetime and last 90 days.

`data/catalog_pre.json` was captured 2026-08-23, before the switch:
110 videos, 3,956,757 total public views.

The tracked 20 are pinned from that file, so the before and after compare like
for like even if the ranking shifts.

## Two questions this is built to answer

**Where is the engaged threshold?** YouTube says only "some amount of seconds"
after the first frame. It is not 30 seconds, that figure was always about ads.
Compare each video's post-switch engaged ratio against its own first-bucket watch
ratio across 20 videos and the threshold falls out. Bucket width is 1% of runtime,
so shorter videos resolve it more tightly.

**Does retention itself drop on the 24th?** Retention is a ratio whose denominator
is "people who viewed". If YouTube recomputes it against the new first-frame
count, every retention graph on the platform falls overnight with no video
changing. `averageViewPercentage` is logged daily and the full curves on every
new-day event, so the before/after is on record.

## Setup

Repo secrets: `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` from
`youtube-oauth.json`, and `DISCORD_WEBHOOK_URL` from
`view-lag-probe-webhook.json`. The refresh token already carries both
`youtube.force-ssl` and `yt-analytics.readonly`.

## Known limits

- Analytics has no time dimension finer than `day`. `month` is the only other
  one. There is no faster source: Studio's Realtime card is views-only and has no
  API, and the bulk Reporting API is slower.
- GitHub Actions schedules are best-effort and drift 5-20 minutes under load.
  Every row stamps its own UTC time, so drift widens resolution rather than
  corrupting it.
- On this channel pre-switch, every sub-100% engaged ratio was Shorts
  contamination. Shorts sat at 22.6% while every long-form source was 97-100%.
  Any estimate has to weight by traffic mix rather than use one flat average.
