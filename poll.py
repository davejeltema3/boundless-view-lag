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
import re
import sys
import datetime
import statistics
import time
import urllib.request
import urllib.parse
import urllib.error

ROOT = os.path.dirname(os.path.abspath(__file__))
# DATA_DIR lets a local test run write somewhere harmless. Without it, every
# manual run dirties the repo's data/ folder, which then has to be discarded by
# hand before committing, and worse, can collide with what the workflow writes.
DATA = os.environ.get("DATA_DIR") or os.path.join(ROOT, "data")
SNAPSHOTS = os.path.join(DATA, "snapshots.jsonl")
CHANGES = os.path.join(DATA, "changes.jsonl")
RETENTION = os.path.join(DATA, "retention.jsonl")
STATE = os.path.join(DATA, "state.json")
CATALOG_PRE = os.path.join(DATA, "catalog_pre.json")
# Append-only record of what has already been announced. Lives in its own file
# because state.json gets reverted whenever a merge conflict resolves, which is
# what made the same NEW DAY alert fire twice and made revisions ping-pong
# forever. This file union-merges and therefore never conflicts.
ANNOUNCED = os.path.join(DATA, "announced.jsonl")
PULSE = os.path.join(DATA, "pulse.csv")
TICKS = os.path.join(DATA, "ticks.csv")

# Full snapshots are ~9KB. At 5-minute cadence that is 2.6MB/day into git, so the
# heavy record is written hourly or on any change, while a one-line pulse row goes
# down every single run. The pulse is what the rate analysis actually needs.
FULL_SNAPSHOT_EVERY_MIN = 60

# GitHub throttles */5 schedules hard -- observed roughly one run per hour. So a
# run no longer polls once and exits: it holds the runner and samples on its own
# clock until the window closes. A tick is a single channels.list call, 1 quota
# unit, which keeps 1-minute resolution affordable (1,440 units/day).
# Silence used to be ambiguous: no alert meant either nothing moved or the probe
# was dead. Twice it was dead. A heartbeat makes the difference visible.
HEARTBEAT_HOURS = float(os.environ.get("HEARTBEAT_HOURS", "6"))
LOOP_MINUTES = int(os.environ.get("LOOP_MINUTES", "0"))
TICK_SECONDS = int(os.environ.get("TICK_SECONDS", "60"))

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
    raw = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                raw = r.read()
            break
        except urllib.error.HTTPError as e:
            die("HTTP %s on %s\n%s" % (e.code, url.split("?")[0], e.read().decode()[:800]))
        except Exception as exc:
            # A transient network blip must not end a run that holds for hours.
            if attempt == 2:
                die("network error on %s after 3 tries: %s"
                    % (url.split("?")[0], exc))
            time.sleep(2 * (attempt + 1))
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
                           "avgDuration": row[4],
                           # The API returns 28.45 but float round-tripping stores
                           # it as 28.449999999999996, which read as a change on
                           # every run and spammed Discord forever.
                           "avgViewPct": round(row[5], 2)}

    # --- day x video for all tracked videos, in ONE call ---
    vid_days = {}
    if vids:
        for row in analytics(token, "views,engagedViews,averageViewPercentage",
                             "day,video", start, end,
                             filters="video==" + ",".join(vids), sort="day", maxr=500):
            vid_days.setdefault(row[1], {})[row[0]] = {
                "views": row[2], "engagedViews": row[3],
                "avgViewPct": round(row[4], 2)}

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


def tick_ids(public):
    """The 50 videos carrying current traffic: the 35 newest plus the 15 biggest.
    `public` is built by walking the uploads playlist, which is newest-first, and
    dicts keep insertion order, so the leading keys are the recent uploads.
    One videos.list call covers 50 ids for a single quota unit."""
    keys = list(public)
    newest = keys[:35]
    biggest = sorted(keys, key=lambda v: -public[v][0])[:15]
    out = []
    for v in newest + biggest:
        if v not in out:
            out.append(v)
    return out[:50]


def tick(token, ids):
    """One quota unit. The channel-level aggregate is cached and can sit still for
    minutes, so this sums a fixed set of videos instead -- that number moves within
    seconds and is what actually reveals a step change in counting."""
    total = 0
    for it in get(DATA_API + "/videos",
                  {"part": "statistics", "id": ",".join(ids)}, token).get("items", []):
        total += int(it["statistics"].get("viewCount", 0))
    if not os.path.exists(TICKS):
        with open(TICKS, "w") as f:
            f.write("ts,tracked50_views,n_videos\n")
    with open(TICKS, "a") as f:
        f.write("%s,%d,%d\n" % (
            datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            total, len(ids)))
    return total


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
        if round(old.get("avgViewPct") or 0, 2) != round(row.get("avgViewPct") or 0, 2):
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


def alert_key(line):
    """A stable id for something we have already told Dave about.

    Revisions are normalised so 8,896 -> 8,789 and 8,789 -> 8,896 share one key.
    Without that, a reverting state file reports the same pair back and forth
    forever, which is most of the Discord noise."""
    if line.startswith("NEW DAY"):
        return "newday:" + line.split()[2]
    if line.startswith("REVISED"):
        parts = line.split()
        day, metric = parts[1], parts[2].rstrip(":")
        # Only the values after the metric name. Scanning the whole line pulls
        # digits out of the date and makes keys that could collide.
        tail = line.split(":", 1)[1] if ":" in line else line
        nums = sorted(int(x.replace(",", "")) for x in re.findall(r"[\d,]+", tail)
                      if x.replace(",", "").isdigit())
        if len(nums) >= 2:
            return "rev:%s:%s:%d:%d" % (day, metric, nums[0], nums[-1])
        return "rev:" + day + ":" + metric
    return None


def load_announced():
    seen = set()
    if os.path.exists(ANNOUNCED):
        try:
            for l in open(ANNOUNCED, encoding="utf-8"):
                if l.strip():
                    seen.add(json.loads(l)["k"])
        except (ValueError, OSError):
            pass
    return seen


def save_announced(keys, ts):
    if not keys:
        return
    os.makedirs(DATA, exist_ok=True)
    with open(ANNOUNCED, "a") as f:
        for k in keys:
            f.write(json.dumps({"ts": ts, "k": k}) + "\n")


def humanise(lines, cur):
    """Turn diff lines into something readable at a glance.

    Returns (emoji, headline, body, colour, meaning)."""
    new_days = [l for l in lines if l.startswith("NEW DAY")]
    revs = [l for l in lines if l.startswith("REVISED")]
    jumps = [l for l in lines if l.startswith("RATE JUMP")]
    alive = [l for l in lines if l.startswith("still alive")]
    first = [l for l in lines if l.startswith("first run")]

    if jumps:
        return ("\u26a1", "Public view rate jumped", jumps[0], 0xef4444,
                "The public counter sped up sharply. This is the tripwire for a "
                "change in how YouTube counts.")

    if new_days:
        l = new_days[0]
        day = l.split()[2]
        row = cur["channel_days"].get(day, {})
        v, e = row.get("views", 0), row.get("engagedViews", 0)
        pct = row.get("avgViewPct")
        if not v:
            # State can be stale or reverted, so read the numbers back out of the
            # alert line rather than reporting zeros.
            m = re.search(r"views ([\d,]+) / engaged ([\d,]+)", l)
            if m:
                v = int(m.group(1).replace(",", ""))
                e = int(m.group(2).replace(",", ""))
            m2 = re.search(r"avg view % ([\d.]+)", l)
            if m2:
                pct = float(m2.group(1))
        gap = (100.0 * (v - e) / v) if v else 0.0
        lag = cur.get("lag_hours")
        body = ("**%s** is now available, %.0f hours after that day ended.\n\n"
                "Views: **%s**\nEngaged views: **%s**\nGap: **%.2f%%**\n"
                "Average view percentage: %s"
                % (day, lag or 0, fmt(v), fmt(e), gap,
                   ("%.1f%%" % pct) if pct is not None else "not reported"))
        meaning = ("Out of every 100 views, about %.0f counted as engaged."
                   % (100 - gap))
        if revs:
            body += "\n\n_%d earlier day%s also adjusted._" % (
                len(revs), "" if len(revs) == 1 else "s")
        return ("\U0001f4c5", "New day of data: " + day, body, 0x22c55e, meaning)

    if revs:
        biggest, size = revs[0], 0
        for l in revs:
            nums = [int(x.replace(",", "")) for x in re.findall(r"[\d,]+", l)
                    if x.replace(",", "").isdigit()]
            if len(nums) >= 2 and abs(nums[-1] - nums[-2]) > size:
                size, biggest = abs(nums[-1] - nums[-2]), l
        days = sorted({l.split()[1] for l in revs})
        body = "%d earlier day%s changed: %s\n\n`%s`" % (
            len(revs), "" if len(revs) == 1 else "s", ", ".join(days), biggest)
        return ("\U0001f501", "Earlier numbers revised", body, 0xf59e0b,
                "YouTube keeps adjusting past days for roughly five days. "
                "Normal, but it means a single read is never final.")

    if first:
        return ("\U0001f195", "Baseline captured", first[0], 0x8b5cf6,
                "Starting point recorded. Future alerts compare against this.")

    if alive:
        return ("\U0001f4a4", "Nothing new", alive[0], 0x64748b,
                "The probe is running. No data moved since the last check.")

    return ("\u2139", "Update", "\n".join(lines[:8]), 0x8b5cf6, "")


def post_discord(lines, cur):
    url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not url or not lines:
        return
    emoji, headline, body, colour, meaning = humanise(lines, cur)
    desc = body
    if meaning:
        desc += "\n\n> " + meaning
    embed = {
        "title": "%s  %s" % (emoji, headline),
        "description": desc[:3800],
        "color": colour,
        "fields": [
            {"name": "Latest day of data", "value":
                str(cur.get("latest_analytics_day")), "inline": True},
            {"name": "How far behind", "value":
                "%.0f hours" % (cur.get("lag_hours") or 0), "inline": True},
            {"name": "Views right now", "value":
                fmt(cur["catalog_views"]), "inline": True},
        ],
        "footer": {"text": "view-lag probe  \u00b7  green = new day, "
                           "amber = revision, red = rate jump, grey = all quiet"},
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

    # Drop anything already announced. Without this, a reverted state file
    # re-reports the same NEW DAY and bounces the same revision back and forth.
    seen = load_announced()
    fresh_keys = []
    kept = []
    for l in lines:
        k = alert_key(l)
        if k is None:
            kept.append(l)
        elif k not in seen:
            kept.append(l)
            fresh_keys.append(k)
    suppressed = len(lines) - len(kept)
    if suppressed:
        print("  suppressed %d already-announced alert(s)" % suppressed)
    lines = kept

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
        save_announced(fresh_keys, cur["ts"])
        cur["_last_ping"] = cur["ts"]
    else:
        last_ping = (prev or {}).get("_last_ping")
        due = True
        if last_ping:
            age = (datetime.datetime.fromisoformat(cur["ts"])
                   - datetime.datetime.fromisoformat(last_ping)).total_seconds() / 3600.0
            due = age >= HEARTBEAT_HOURS
        if due:
            post_discord(["still alive, nothing moved. latest analytics day %s, "
                          "lag %sh, catalog %s views"
                          % (cur["latest_analytics_day"], cur["lag_hours"],
                             fmt(cur["catalog_views"]))], cur)
            cur["_last_ping"] = cur["ts"]
        else:
            cur["_last_ping"] = last_ping

    cur["_rates"] = [round(r, 2) for r in rates]
    with open(STATE, "w") as f:
        json.dump(cur, f, indent=1)

    if LOOP_MINUTES > 0:
        ids = tick_ids(cur["public"])
        print("holding %d min, ticking every %ds over %d videos"
              % (LOOP_MINUTES, TICK_SECONDS, len(ids)))
        # The ticks are already on disk and the commit step runs on always(), so
        # an exception in here costs no data. Failing the job over it only
        # produces an alert that means nothing. Log it loudly instead, and print
        # a marker so a clean finish is distinguishable from a crash.
        try:
            hold_and_tick(token, ids, LOOP_MINUTES, TICK_SECONDS)
        except Exception as exc:
            import traceback
            print("HOLD ABORTED: %r" % (exc,), file=sys.stderr)
            traceback.print_exc()
            print("ticks up to the failure are still on disk and will be committed")

    print("RUN COMPLETE ok")


if __name__ == "__main__":
    main()
