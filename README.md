# boundless-view-lag

A throwaway research probe with one job: find out how often the YouTube Analytics
API actually refreshes `engagedViews`, and how far behind real time it runs.

Context: on 2026-08-24 YouTube started counting a view from the first frame on
long-form and live, and the old methodology survives as `engagedViews` in
Analytics only. If a video's title is going to display both numbers, we need to
know how stale the engaged number is at any moment.

## What it does

Every 15 minutes:

1. Refreshes an OAuth access token.
2. Reads public counters from the Data API (channel views/subs, plus
   views/likes/comments for the 5 videos with the most traffic in the window).
3. Reads a day-level series from the Analytics API: `views`, `engagedViews`,
   `estimatedMinutesWatched`, `averageViewDuration`, at channel level and per video.
4. Diffs against the previous run.
5. Appends the snapshot to `data/snapshots.jsonl`, and if anything moved, appends
   to `data/changes.jsonl` and pings Discord.

Two kinds of change matter:

- **NEW DAY** — a day that wasn't available before now is. The timestamp on that
  event is the answer to "how long is the lag."
- **REVISED** — a day that was already reported changed value. Tells us whether
  numbers keep settling after they first appear.

## Setup

Repo secrets (Settings > Secrets and variables > Actions):

| Secret | Where it comes from |
|---|---|
| `YT_CLIENT_ID` | `youtube-oauth.json` |
| `YT_CLIENT_SECRET` | `youtube-oauth.json` |
| `YT_REFRESH_TOKEN` | `youtube-oauth.json` |
| `DISCORD_WEBHOOK_URL` | channel webhook, optional |

The refresh token already carries both `youtube.force-ssl` and
`yt-analytics.readonly`, so no new consent is needed.

Then Actions > "view-lag probe" > Run workflow, to seed the baseline.

## Knobs

- `cron: "*/15"` in the workflow. GitHub's hard floor is 5 minutes.
- `LOOKBACK_DAYS` (default 10) — how many days back each snapshot covers.
- `TRACK_VIDEO_IDS` — comma-separated, pins specific videos instead of
  auto-picking the top 5 by recent views.
- `DRY_RUN=1` locally — prints the snapshot, writes nothing, pings nothing.

## Local run

```
export YT_CLIENT_ID=... YT_CLIENT_SECRET=... YT_REFRESH_TOKEN=...
DRY_RUN=1 python3 poll.py
```

No dependencies. Standard library only.

## Known limits

- Analytics API has no dimension finer than `day`. `month` is the only other
  time dimension. So a day-level number refreshing on some cadence is the ceiling,
  and there is no faster source: Studio's realtime tab is views-only, and the bulk
  Reporting API is slower, not faster.
- GitHub Actions schedules are best-effort and can drift 5-20 minutes under load.
  Each snapshot stamps its own UTC timestamp, so drift widens resolution rather
  than corrupting the measurement.
- Scheduled workflows in a repo with no activity for 60 days get disabled by
  GitHub. Not a concern for a probe measured in weeks.
- Quota: each poll costs a handful of Data API units against the 10,000/day
  project budget. The Analytics API is a separate service with its own quota, so
  polling does not eat into the budget a future title-updater would need.

## Baseline captured 2026-08-23 (pre-change)

```
day          views  engaged   gap
2026-08-15    5264     5256   0.2%
2026-08-16    5703     5698   0.1%
2026-08-17    6474     6460   0.2%
2026-08-18    5790     5780   0.2%
2026-08-19   12812    12633   1.4%
2026-08-20    7114     7036   1.1%
2026-08-21    8896     8802   1.1%
```

At 2026-08-23 20:25 UTC the latest available day was 2026-08-21, a lag of 44.4 hours.
