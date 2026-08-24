#!/usr/bin/env python3
"""
Boundless view-lag probe.

Two jobs:

1. Measure how often the YouTube Analytics API refreshes `engagedViews`, and how
   far behind real time it runs. Answered by timestamping the moment each new
   day becomes available.

2. Capture the 2026-08-24 view-counting switch at 5-minute resolution while it
   happens. YouTube's notice says the pre-switch public view count "will no
   longer be accessible via the YouTube Public Data API" afterwards, so the
   catalog-wide public counters recorded here cannot be reconstructed later.

Env:
  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN   (required)
  DISCORD_WEBHOOK_URL                                (optional)
  LOOKBACK_DAYS     default 12
  TOP_N             default 20
  TRACK_VIDEO_IDS   comma-separated, overrides the pinned set
  DRY_RUN=1         print, write nothing, ping nothing
"""

import json
import os
import sys
import datetime
import statistics
import urllib.request
import urllib.parse
import urllib.error

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
SNAPSHOTS = os.path.join(DATA, "snapshots.jsonl")
CHANGES = os.path.join(DATA, "changes.jsonl")
RETENTION = os.path.join(DATA, "retention.jsonl")
STATE = os.path.join(DATA, "state.json")
CATALOG_PRE = os.path.join(DATA, "catalog_pre.json")
PULSE = os.path.join(DATA, "pulse.csv")

# Full snapshots are ~9KB. At 5-minute cadence that is 2.6MB/day into git, so the
# heavy record is written hourly or on any change, while a one-line pulse row goes
# down every single run. The pulse is what the rate analysis actually needs.
FULL_SNAPSHOT_EVERY_MIN = 60

DRY = os.environ.get("DRY_RUN") == "1"
LOOKBACK = int(os.environ.get("LOOKBACK_DAYS", "12"))
TOP_N = int(os.environ.get("TOP_N", "20"))

DATA_API = "https://www.googleapis.com/youtube/v3"
ANALYTICS_API = "https://youtubeanalytics.googleapis.com/v2/reports"
TOKEN_URL = "https://oauth2.googleapis.com/token"

# Rate-jump alerting. The switch should show up as a step change in views/hour
# across the whole catalog, so this is the tripwire for "it just happened".
RATE_SAMPLES = 12
RATE_MULTIPLE = 1.75
RATE_MIN_DELTA = 40


def die(msg):
    print("FATAL: " + msg, file=sys.stderr)
    sys.exit(1)


def http(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        die("HTTP %s on %s\n%s" % (e.code, url.split("?")[0], e.read().decode()[:800]))
    # Discord webhooks answer 204 with an empty body. Google always sends JSON.
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except ValueError:
        return {"raw": raw.decode("utf-8", "replace")[:500]}


def access_token():
    for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"):
        if not os.environ.get(k):
            die("missing env var " + k)
    body = urllib.parse.urlencode({
        "client_id": os.environ["YT_CLIENT_ID"],
        "client_secret": os.environ["YT_CLIENT_SECRET"],
        "refresh_token": os.environ["YT_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }).encode()
    return http(TOKEN_URL, data=body)["access_token"]


def get(url, params, token):
    return http(url + "?" + urllib.parse.urlencode(params),
                headers={"Authorization": "Bearer " + token})


def analytics(token, metrics, dimensions, start, end,
              filters=None, sort=None, maxr=None):
    p = {"ids": "channel==MINE", "startDate": start, "endDate": end,
         "metrics": metrics, "dimensions": dimensions}
    if filters:
        p["filters"] = filters
    if sort:
        p["sort"] = sort
    if maxr:
        p["maxResults"] = str(maxr)
    return get(ANALYTICS_API, p, token).get("rows", [])


def catalog_ids(token):
    ch = get(DATA_API + "/channels",
             {"part": "contentDetails,statistics", "mine": "true"}, token)["items"][0]
    up = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, page = [], None
    while True:
        p = {"part": "contentDetails", "playlistId": up, "maxResults": "50"}
        if page:
            p["pageToken"] = page
        r = get(DATA_API + "/playlistItems", p, token)
        ids += [i["contentDetails"]["videoId"] for i in r.get("items", [])]
        page = r.get("nextPageToken")
        if not page:
            return ids, ch["statistics"]


def tracked_videos(life_rows):
    """Pinned to the pre-change top N so before and after compare like for like."""
    env = os.environ.get("TRACK_VIDEO_IDS", "").strip()
    if env:
        return [v.strip() for v in env.split(",") if v.strip()]
    if os.path.exists(CATALOG_PRE):
        try:
            with open(CATALOG_PRE) as f:
                life = json.load(f)["lifetime_analytics"]
            return [v for v, _ in sorted(life.items(),
                                         key=lambda kv: -kv[1]["views"])[:TOP_N]]
        except Exception as exc:
            print("catalog_pre unreadable (%s), falling back" % exc, file=sys.stderr)
    return [r[0] for r in life_rows[:TOP_N]]


def retention_curves(token, vids, start, end):
    """100-bucket curve per video. Bucket width is 1% of runtime, so a 15-minute
    video gives ~9s buckets. Closest available proxy for the sub-30s dropoff that
    an engaged view actually measures."""
    out = {}
    for vid in vids:
        rows = analytics(token, "audienceWatchRatio,relativeRetentionPerformance",
                         "elapsedVideoTimeRatio", start, end, filters="video==" + vid)
        if rows:
            out[vid] = [[round(r[0], 2), round(r[1], 4), round(r[2], 4)] for r in rows]
    return out


def snapshot(token):
    now = datetime.datetime.now(datetime.timezone.utc)
    today = now.date()
    start = (today - datetime.timedelta(days=LOOKBACK)).isoformat()
    end = today.isoformat()

    ids, ch_stats = catalog_ids(token)

    # --- public counters for the WHOLE catalog, not a sample ---
    public = {}
    for i in range(0, len(ids), 50):
        for it in get(DATA_API + "/videos",
                      {"part": "statistics", "id": ",".join(ids[i:i + 50])},
                      token).get("items", []):
            s = it["statistics"]
            public[it["id"]] = [int(s.get("viewCount", 0)),
                                int(s.get("likeCount", 0)),
                                int(s.get("commentCount", 0))]
    catalog_views = sum(v[0] for v in public.values())

    # --- which videos get the day-level analytics treatment ---
    life_rows = analytics(token, "views", "video", start, end, sort="-views", maxr=50)
    vids = tracked_videos(life_rows)

    # --- channel day series ---
    ch_days = {}
    for row in analytics(token,
                         "views,engagedViews,estimatedMinutesWatched,"
                         "averageViewDuration,averageViewPercentage",
                         "day", start, end, sort="day"):
        ch_days[row[0]] = {"views": row[1], "engagedViews": row[2], "minutes": row[3],
                           "avgDuration": row[4], "avgViewPct": row[5]}

    # --- day x video for all tracked videos, in ONE call ---
    vid_days = {}
    if vids:
        for row in analytics(token, "views,engagedViews,averageViewPercentage",
                             "day,video", start, end,
                             filters="video==" + ",".join(vids), sort="day", maxr=500):
            vid_days.setdefault(row[1], {})[row[0]] = {
                "views": row[2], "engagedViews": row[3], "avgViewPct": row[4]}

    # --- day x traffic source ---
    traffic_days = {}
    for row in analytics(token, "views,engagedViews", "day,insightTrafficSourceType",
                         start, end, sort="day", maxr=500):
        traffic_days.setdefault(row[0], {})[row[1]] = {"views": row[2],
                                                       "engagedViews": row[3]}

    latest = max(ch_days) if ch_days else None
    lag_hours = None
    if latest:
        day_end = datetime.datetime.fromisoformat(latest + "T23:59:59+00:00")
        lag_hours = round((now - day_end).total_seconds() / 3600.0, 2)

    return {
        "ts": now.isoformat(timespec="seconds"),
        "channel_public": {k: int(v) for k, v in ch_stats.items() if str(v).isdigit()},
        "catalog_views": catalog_views,
        "catalog_size": len(public),
        "public": public,
        "tracked_vids": vids,
        "range": [start, end],
        "latest_analytics_day": latest,
        "lag_hours": lag_hours,
        "channel_days": ch_days,
        "video_days": vid_days,
        "traffic_days": traffic_days,
    }


def fmt(n):
    return "{:,}".format(n)


def diff(prev, cur, rates):
    out = []
    if not prev:
        return ["first run: baseline captured, latest analytics day %s (lag %sh), "
                "catalog %s views across %d videos"
                % (cur["latest_analytics_day"], cur["lag_hours"],
                   fmt(cur["catalog_views"]), cur["catalog_size"])]

    # 1. a new analytics day appeared
    if cur["latest_analytics_day"] != prev.get("latest_analytics_day"):
        d = cur["latest_analytics_day"]
        row = cur["channel_days"].get(d, {})
        v, e = row.get("views", 0), row.get("engagedViews", 0)
        gap = (100.0 * (v - e) / v) if v else 0.0
        out.append("NEW DAY %s appeared (lag %sh) -- views %s / engaged %s / gap %.1f%% "
                   "/ avg view %% %s"
                   % (d, cur["lag_hours"], fmt(v), fmt(e), gap, row.get("avgViewPct")))

    # 2. a previously-reported day changed value
    for d, row in sorted(cur["channel_days"].items()):
        old = prev.get("channel_days", {}).get(d)
        if not old or (d == cur["latest_analytics_day"]
                       and d != prev.get("latest_analytics_day")):
            continue
        for k in ("views", "engagedViews"):
            if old.get(k) != row.get(k):
                out.append("REVISED %s %s: %s -> %s (%+d)"
                           % (d, k, fmt(old.get(k, 0)), fmt(row.get(k, 0)),
                              row.get(k, 0) - old.get(k, 0)))
        if old.get("avgViewPct") != row.get("avgViewPct"):
            out.append("REVISED %s avgViewPct: %s -> %s"
                       % (d, old.get("avgViewPct"), row.get("avgViewPct")))

    # 3. public view rate step change -- the tripwire for the counting switch
    delta = cur["catalog_views"] - prev.get("catalog_views", cur["catalog_views"])
    hours = (datetime.datetime.fromisoformat(cur["ts"])
             - datetime.datetime.fromisoformat(prev["ts"])).total_seconds() / 3600.0
    if hours > 0:
        rate = delta / hours
        if len(rates) >= 4 and delta >= RATE_MIN_DELTA:
            base = statistics.median(rates)
            if base > 0 and rate > RATE_MULTIPLE * base:
                out.append("RATE JUMP public views running at %.0f/hr vs trailing "
                           "median %.0f/hr (%.1fx) -- %+d views in %.0f min"
                           % (rate, base, rate / base, delta, hours * 60))
    return out


def post_discord(lines, cur):
    url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not url or not lines:
        return
    head = lines[0]
    if head.startswith("RATE JUMP"):
        event, color = "Public view rate jumped", 0xef4444
    elif head.startswith("NEW DAY"):
        event, color = "New day appeared", 0x22c55e
    elif head.startswith("REVISED"):
        event, color = "Day revised", 0xf59e0b
    else:
        event, color = "Baseline captured", 0x8b5cf6

    body = "\n".join("- " + l for l in lines[:15])
    if len(lines) > 15:
        body += "\n- ...and %d more" % (len(lines) - 15)

    embed = {
        "title": "\U0001f4c9 Engaged Views Probe",
        "description": body[:3800],
        "color": color,
        "fields": [
            {"name": "Event", "value": event, "inline": True},
            {"name": "Latest day", "value": str(cur.get("latest_analytics_day")),
             "inline": True},
            {"name": "Lag", "value": "%sh" % cur.get("lag_hours"), "inline": True},
            {"name": "Catalog views (live)", "value": fmt(cur["catalog_views"]),
             "inline": True},
        ],
        "footer": {"text": "boundless-view-lag"},
        "timestamp": cur["ts"],
    }
    try:
        http(url, data=json.dumps({"embeds": [embed]}).encode(), headers={
            "Content-Type": "application/json",
            "User-Agent": "boundless-view-lag/1.0 (+github actions probe)",
        })
    except Exception as exc:
        print("discord post failed (%s), continuing" % exc, file=sys.stderr)


def main():
    token = access_token()
    cur = snapshot(token)

    prev, rates = None, []
    if os.path.exists(STATE):
        # A corrupt state file must never kill the probe. A merge that leaves
        # conflict markers in here once cost us every run until someone noticed,
        # because the crash happened before anything was logged. Treat an
        # unreadable state as a first run and carry on.
        try:
            with open(STATE) as f:
                prev = json.load(f)
            rates = prev.get("_rates", [])
        except (ValueError, OSError) as exc:
            print("state.json unreadable (%s) -- treating as first run" % exc,
                  file=sys.stderr)
            prev, rates = None, []

    lines = diff(prev, cur, rates)

    # roll the rate history forward
    if prev:
        hrs = (datetime.datetime.fromisoformat(cur["ts"])
               - datetime.datetime.fromisoformat(prev["ts"])).total_seconds() / 3600.0
        if hrs > 0:
            rates = (rates + [(cur["catalog_views"] - prev.get("catalog_views", 0)) / hrs])
            rates = rates[-RATE_SAMPLES:]

    print("ts=%s latest_day=%s lag=%sh catalog=%s (%d videos)"
          % (cur["ts"], cur["latest_analytics_day"], cur["lag_hours"],
             fmt(cur["catalog_views"]), cur["catalog_size"]))
    for l in lines:
        print("  CHANGE: " + l)
    if not lines:
        print("  no change")

    if DRY:
        return

    os.makedirs(DATA, exist_ok=True)

    # one compact row every run
    if not os.path.exists(PULSE):
        with open(PULSE, "w") as f:
            f.write("ts,catalog_views,subscribers,latest_analytics_day,lag_hours,catalog_size\n")
    with open(PULSE, "a") as f:
        f.write("%s,%d,%s,%s,%s,%d\n" % (
            cur["ts"], cur["catalog_views"],
            cur["channel_public"].get("subscriberCount", ""),
            cur["latest_analytics_day"], cur["lag_hours"], cur["catalog_size"]))

    # full snapshot on change, hourly otherwise
    last_full = (prev or {}).get("_last_full")
    due = True
    if last_full and not lines:
        age = (datetime.datetime.fromisoformat(cur["ts"])
               - datetime.datetime.fromisoformat(last_full)).total_seconds() / 60.0
        due = age >= FULL_SNAPSHOT_EVERY_MIN
    if due:
        with open(SNAPSHOTS, "a") as f:
            f.write(json.dumps(cur) + "\n")
        cur["_last_full"] = cur["ts"]
    else:
        cur["_last_full"] = last_full

    if any(l.startswith(("NEW DAY", "first run")) for l in lines):
        s, e = cur["range"]
        curves = retention_curves(token, cur["tracked_vids"], s, e)
        if curves:
            with open(RETENTION, "a") as f:
                f.write(json.dumps({"ts": cur["ts"],
                                    "day": cur["latest_analytics_day"],
                                    "curves": curves}) + "\n")
            print("  captured retention curves for %d videos" % len(curves))

    if lines:
        with open(CHANGES, "a") as f:
            f.write(json.dumps({"ts": cur["ts"], "changes": lines}) + "\n")
        post_discord(lines, cur)

    cur["_rates"] = [round(r, 2) for r in rates]
    with open(STATE, "w") as f:
        json.dump(cur, f, indent=1)


if __name__ == "__main__":
    main()
