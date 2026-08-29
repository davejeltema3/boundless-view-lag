# What happened when YouTube changed how it counts views

On 2026-08-24 YouTube changed the definition of a view. A view now counts from
the first frame across long-form, live and Shorts. The previous definition, which
required the viewer to actually stay, survives as **engaged views** inside
Analytics.

YouTube's developer notice states that the pre-switch public view count **"will
no longer be accessible via the YouTube Public Data API"** afterwards.

That makes the before-picture a one-time capture. This repository is that capture,
plus the instrumentation that watched the change happen, plus the findings and a
falsifiable prediction recorded before the data existed to check it.

**Start here:** [FINDINGS.md](FINDINGS.md) for what was measured.
[PREDICTION.md](PREDICTION.md) for the claim made in advance.

---

## Why this exists

Anyone can describe the change now. Almost nobody can show what the numbers looked
like the day before, with commit timestamps to prove the record predates the event.

The baseline was captured on 2026-08-23: a full channel catalogue, retention
curves, traffic splits, and two baskets of other channels ranging from tens of
subscribers to hundreds of thousands. Then a probe sampled the live public view
counter every 60 seconds through the switch and kept going.

## What the probe does

Every run refreshes an OAuth token, then:

1. Reads public view, like and comment counts for the **whole catalogue**, not a
   sample.
2. Reads a day-level Analytics series: `views`, `engagedViews`,
   `estimatedMinutesWatched`, `averageViewDuration`, `averageViewPercentage`.
3. Reads `day x video` for the tracked set, and `day x insightTrafficSourceType`.
4. On a new-day event, captures 100-bucket retention curves per tracked video.
5. Holds the runner and samples a fixed set of videos every 60 seconds, because
   the interesting behaviour happens between the daily rows.

It raises three kinds of event: a **new day** of Analytics becoming queryable
(the timestamp on that is the lag measurement), a **revision** to a day already
reported, and a **rate jump** in the public counter.

Analytics is private channel data, so this needs the channel owner's OAuth
refresh token. An API key cannot reach it.

## What's in `data/`

| File | Contents |
|---|---|
| `catalog_pre.json` | the pre-switch capture: every video's public counters, lifetime views vs engaged views, retention curves, traffic and device splits |
| `basket_pre.json` | reference channels in one niche, wide size range, public data, captured pre-switch |
| `basket_clients_anon.json` | a second basket of small channels, anonymised (see below) |
| `pulse.csv` | one row per run: timestamp, catalogue views, subscribers, latest available day, lag in hours |
| `ticks.csv` | 60-second samples of the live public counter on a fixed video set |
| `snapshots.jsonl` | full snapshots, hourly or on any change |
| `changes.jsonl` | only the runs where something moved |
| `retention.jsonl` | 100-bucket retention curves, captured on new-day events |

## A note on the anonymised basket

`basket_clients_anon.json` holds 30 real channels captured before the switch,
spanning roughly 40 to 14,000 subscribers. Their identities are removed because
their relationship to the author is confidential, and several are small enough
that naming them would identify individuals.

Channel and video identifiers are salted hashes, stable within the file so
before-and-after comparisons still work. Subscriber counts, view counts, like
counts, comment counts and durations are unmodified. Nothing needed for the
size-versus-inflation analysis was removed.

The identity list itself is gitignored. `clients.txt.example` shows the format if
you want to run the same capture on your own channels.

## Running it yourself

```
pip install nothing        # standard library only
export YT_CLIENT_ID=...    # OAuth client for a Google Cloud project with
export YT_CLIENT_SECRET=...#   YouTube Data API v3 and YouTube Analytics API enabled
export YT_REFRESH_TOKEN=...#   scopes: youtube.force-ssl, yt-analytics.readonly
export DISCORD_WEBHOOK_URL=...   # optional, for alerts

DRY_RUN=1 python3 poll.py                    # single poll, writes nothing
LOOP_MINUTES=170 python3 poll.py             # hold and sample every 60s
LABEL=pre python3 capture_baseline.py        # deep one-off capture
LABEL=pre BASKET_FILE=basket.txt python3 capture_basket.py
```

`DATA_DIR` redirects output somewhere harmless for local testing.

Quota: roughly 7 Data API units per run against a 10,000/day budget. The
Analytics API is metered separately.

## Known limits

Read these before drawing conclusions from anything here.

- **One primary channel.** Long-form, subscriber-heavy, education niche. A
  browse-heavy or Shorts-heavy channel may behave differently.
- **Days keep being revised** for roughly five days after they first appear, by
  more than 1% in observed cases. A single read is never final, and reading early
  produced a materially wrong answer about the size of the change.
- **No dimension finer than `day`** exists in the Analytics API, and Studio's
  realtime card shows views only, never engaged views. The 60-second sampling is a
  workaround, not a supported feature.
- **Scheduled runs are best-effort.** Every row stamps its own UTC time, so gaps
  widen resolution rather than corrupting it.

## Licence

Data and findings are free to use with attribution. If you reuse a number, link
the file it came from so the reader can check the commit date.
