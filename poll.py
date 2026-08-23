#!/usr/bin/env python3
"""
Boundless view-lag probe.

Answers one question: how often does the YouTube Analytics API actually refresh
`engagedViews`, and how far behind real time is it?

Every run takes a full snapshot (public counters from the Data API + day-level
views/engagedViews from the Analytics API), diffs it against the previous run,
appends both to data/, and pings Discord only when something moved.

Env:
  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN   (required)
  DISCORD_WEBHOOK_URL                                (optional)
  TRACK_VIDEO_IDS   comma-separated, optional pin. default = top 5 by recent views
  LOOKBACK_DAYS     default 10
  DRY_RUN=1         print the snapshot, write nothing, ping nothing
"""

import json
import os
import sys
import datetime
import urllib.request
import urllib.parse
import urllib.error

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
SNAPSHOTS = os.path.join(DATA, "snapshots.jsonl")
CHANGES = os.path.join(DATA, "changes.jsonl")
STATE = os.path.join(DATA, "state.json")
RETENTION = os.path.join(DATA, "retention.jsonl")

DRY = os.environ.get("DRY_RUN") == "1"
LOOKBACK = int(os.environ.get("LOOKBACK_DAYS", "10"))

DATA_API = "https://www.googleapis.com/youtube/v3"
ANALYTICS_API = "https://youtubeanalytics.googleapis.com/v2/reports"
TOKEN_URL = "https://oauth2.googleapis.com/token"


def die(msg):
    print("FATAL: " + msg, file=sys.stderr)
    sys.exit(1)


def http(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:800]
        die("HTTP %s on %s\n%s" % (e.code, url.split("?")[0], body))
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


def analytics(token, metrics, dimensions, start, end, filters=None, sort=None, maxr=None):
    p = {
        "ids": "channel==MINE",
        "startDate": start,
        "endDate": end,
        "metrics": metrics,
        "dimensions": dimensions,
    }
    if filters:
        p["filters"] = filters
    if sort:
        p["sort"] = sort
    if maxr:
        p["maxResults"] = str(maxr)
    r = get(ANALYTICS_API, p, token)
    return r.get("rows", [])


def snapshot(token):
    now = datetime.datetime.now(datetime.timezone.utc)
    today = now.date()
    start = (today - datetime.timedelta(days=LOOKBACK)).isoformat()
    end = today.isoformat()

    # --- public counters (Data API) ---
    ch = get(DATA_API + "/channels",
             {"part": "statistics,contentDetails", "mine": "true"}, token)["items"][0]
    ch_stats = ch["statistics"]

    # --- which videos to track ---
    pinned = os.environ.get("TRACK_VIDEO_IDS", "").strip()
    top_rows = analytics(token, "views,engagedViews", "video", start, end,
                         sort="-views", maxr=5)
    if pinned:
        vids = [v.strip() for v in pinned.split(",") if v.strip()]
    else:
        vids = [r[0] for r in top_rows]

    # --- public per-video counters ---
    vpub = {}
    if vids:
        items = get(DATA_API + "/videos",
                    {"part": "statistics,snippet", "id": ",".join(vids)}, token).get("items", [])
        for it in items:
            s = it["statistics"]
            vpub[it["id"]] = {
                "title": it["snippet"]["title"][:80],
                "publishedAt": it["snippet"]["publishedAt"],
                "viewCount": int(s.get("viewCount", 0)),
                "likeCount": int(s.get("likeCount", 0)),
                "commentCount": int(s.get("commentCount", 0)),
            }

    # --- analytics day series, channel level ---
    # averageViewPercentage matters here beyond curiosity: if YouTube recomputes
    # retention against the new first-frame view count, every retention number on
    # the platform drops on 2026-08-24 without any video changing. This catches it.
    ch_days = {}
    for row in analytics(token,
                         "views,engagedViews,estimatedMinutesWatched,"
                         "averageViewDuration,averageViewPercentage",
                         "day", start, end, sort="day"):
        ch_days[row[0]] = {
            "views": row[1], "engagedViews": row[2], "minutes": row[3],
            "avgDuration": row[4], "avgViewPct": row[5],
        }

    # --- analytics day series, per video ---
    vid_days = {}
    for vid in vids:
        d = {}
        for row in analytics(token, "views,engagedViews,averageViewPercentage",
                             "day", start, end, filters="video==" + vid, sort="day"):
            d[row[0]] = {"views": row[1], "engagedViews": row[2], "avgViewPct": row[3]}
        vid_days[vid] = d

    # --- day x traffic source, channel level ---
    # The real-time estimate is only as good as the mix model. Ratios differ hard
    # by source, so hold them per source per day rather than one blended number.
    traffic_days = {}
    for row in analytics(token, "views,engagedViews", "day,insightTrafficSourceType",
                         start, end, sort="day"):
        traffic_days.setdefault(row[0], {})[row[1]] = {"views": row[2], "engagedViews": row[3]}

    latest = max(ch_days) if ch_days else None
    lag_hours = None
    if latest:
        # hours from the END of the latest available day to now
        day_end = datetime.datetime.fromisoformat(latest + "T23:59:59+00:00")
        lag_hours = round((now - day_end).total_seconds() / 3600.0, 2)

    return {
        "ts": now.isoformat(timespec="seconds"),
        "channel_public": {
            "viewCount": int(ch_stats.get("viewCount", 0)),
            "subscriberCount": int(ch_stats.get("subscriberCount", 0)),
            "videoCount": int(ch_stats.get("videoCount", 0)),
        },
        "tracked_vids": vids,
        "range": [start, end],
        "latest_analytics_day": latest,
        "lag_hours": lag_hours,
        "channel_days": ch_days,
        "traffic_days": traffic_days,
        "videos_public": vpub,
        "video_days": vid_days,
    }


def retention_curves(token, vids, start, end):
    """100-bucket retention curve per video. For a 15-minute video each bucket is
    about 9 seconds, so bucket 1 is the closest API proxy for 'did they stay past
    the opening'. Shorter videos give finer resolution."""
    out = {}
    for vid in vids:
        rows = analytics(token, "audienceWatchRatio,relativeRetentionPerformance",
                         "elapsedVideoTimeRatio", start, end, filters="video==" + vid)
        if rows:
            out[vid] = [[round(r[0], 2), round(r[1], 4), round(r[2], 4)] for r in rows]
    return out


def fmt(n):
    return "{:,}".format(n)


def diff(prev, cur):
    """Return a list of human-readable change lines. Empty list = nothing moved."""
    out = []
    if not prev:
        return ["first run: baseline captured, latest analytics day %s (lag %sh)"
                % (cur["latest_analytics_day"], cur["lag_hours"])]

    # 1. a new analytics day appeared -- this is the headline event
    if cur["latest_analytics_day"] != prev.get("latest_analytics_day"):
        d = cur["latest_analytics_day"]
        row = cur["channel_days"].get(d, {})
        v, e = row.get("views", 0), row.get("engagedViews", 0)
        gap = (100.0 * (v - e) / v) if v else 0.0
        out.append("NEW DAY %s appeared (lag %sh) -- views %s / engaged %s / gap %.1f%%"
                   % (d, cur["lag_hours"], fmt(v), fmt(e), gap))

    # 2. a previously-reported day was revised
    for d, row in sorted(cur["channel_days"].items()):
        old = prev.get("channel_days", {}).get(d)
        if not old or d == cur["latest_analytics_day"] and d != prev.get("latest_analytics_day"):
            continue
        for k in ("views", "engagedViews"):
            if old.get(k) != row.get(k):
                out.append("REVISED %s %s: %s -> %s (%+d)"
                           % (d, k, fmt(old.get(k, 0)), fmt(row.get(k, 0)),
                              row.get(k, 0) - old.get(k, 0)))
    return out


def post_discord(lines, cur):
    """Post as Hazel, matching the embed style of the other #dashboard alerts."""
    url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not url or not lines:
        return

    headline = lines[0]
    if headline.startswith("NEW DAY"):
        event, color = "New day appeared", 0x22c55e
    elif headline.startswith("REVISED"):
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
            {"name": "Latest day", "value": str(cur.get("latest_analytics_day")), "inline": True},
            {"name": "Lag", "value": "%sh" % cur.get("lag_hours"), "inline": True},
            {"name": "Public views (live)", "value": fmt(cur["channel_public"]["viewCount"]), "inline": True},
        ],
        "footer": {"text": "boundless-view-lag"},
        "timestamp": cur["ts"],
    }
    try:
        # Discord's edge rejects the default urllib User-Agent with a 403.
        http(url, data=json.dumps({"embeds": [embed]}).encode(), headers={
            "Content-Type": "application/json",
            "User-Agent": "boundless-view-lag/1.0 (+github actions probe)",
        })
    except Exception as exc:  # never let a failed ping kill the run
        print("discord post failed (%s), continuing" % exc, file=sys.stderr)


def main():
    token = access_token()
    cur = snapshot(token)

    prev = None
    if os.path.exists(STATE):
        with open(STATE) as f:
            prev = json.load(f)

    lines = diff(prev, cur)

    print("ts=%s latest_day=%s lag=%sh public_views=%s"
          % (cur["ts"], cur["latest_analytics_day"], cur["lag_hours"],
             fmt(cur["channel_public"]["viewCount"])))
    for l in lines:
        print("  CHANGE: " + l)
    if not lines:
        print("  no change")

    if DRY:
        print(json.dumps(cur, indent=1)[:3000])
        return

    os.makedirs(DATA, exist_ok=True)
    with open(SNAPSHOTS, "a") as f:
        f.write(json.dumps(cur) + "\n")

    # Retention curves are 100 rows per video, so only grab them when the
    # underlying data actually moved to a new day (or on the very first run).
    if any(l.startswith(("NEW DAY", "first run")) for l in lines):
        start, end = cur["range"]
        curves = retention_curves(token, cur["tracked_vids"], start, end)
        if curves:
            with open(RETENTION, "a") as f:
                f.write(json.dumps({"ts": cur["ts"], "day": cur["latest_analytics_day"],
                                    "curves": curves}) + "\n")
            print("  captured retention curves for %d videos" % len(curves))
    if lines:
        with open(CHANGES, "a") as f:
            f.write(json.dumps({"ts": cur["ts"], "changes": lines}) + "\n")
        post_discord(lines, cur)
    with open(STATE, "w") as f:
        json.dump(cur, f, indent=1)


if __name__ == "__main__":
    main()
