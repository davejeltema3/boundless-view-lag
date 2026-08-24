#!/usr/bin/env python3
"""
Snapshot public view counts across a basket of channels, before and after the
2026-08-24 view-counting switch.

Everything here is public Data API data, so it needs no permission from anyone.
That is the point: engaged views are private to each channel owner, but the
public counter inflating is visible for every channel on the platform, and after
the switch there is no way to recover what it said beforehand.

Questions this is built to answer:
  - How much did public view counts inflate?
  - Did that differ by channel size? (the "wider gulf" thesis, testable)
  - Did it differ by long-form-heavy vs Shorts-heavy catalogues?
  - Titles are captured too, so later title edits are detectable (the clickbait
    thesis needs a before-state to measure against).

Usage:  LABEL=pre  python3 capture_basket.py
        LABEL=post python3 capture_basket.py
"""
import json, os, sys, datetime, urllib.request, urllib.parse, urllib.error

DATA_API = "https://www.googleapis.com/youtube/v3"
ROOT = os.path.dirname(os.path.abspath(__file__))
LABEL = os.environ.get("LABEL", "pre")
PER_CHANNEL = int(os.environ.get("PER_CHANNEL", "100"))
BASKET = os.environ.get("BASKET_FILE", os.path.join(ROOT, "basket.txt"))
OUT = os.path.join(ROOT, "data", "basket_%s.json" % LABEL)

_f = os.environ.get("CREDS_FILE")
if _f:
    c = json.load(open(_f))
    creds = {"client_id": c["client_id"], "client_secret": c["client_secret"],
             "refresh_token": c["refresh_token"]}
else:
    creds = {"client_id": os.environ.get("YT_CLIENT_ID"),
             "client_secret": os.environ.get("YT_CLIENT_SECRET"),
             "refresh_token": os.environ.get("YT_REFRESH_TOKEN")}
    if not all(creds.values()):
        sys.exit("set YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN, or CREDS_FILE")

d = urllib.parse.urlencode(dict(creds, grant_type="refresh_token")).encode()
AT = json.load(urllib.request.urlopen(urllib.request.Request(
    "https://oauth2.googleapis.com/token", d)))["access_token"]


def get(path, params):
    u = DATA_API + path + "?" + urllib.parse.urlencode(params)
    for _ in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(
                    u, headers={"Authorization": "Bearer " + AT}), timeout=40) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            print("  HTTP %s %s" % (e.code, e.read().decode()[:150]))
            return {}
        except Exception:
            pass
    return {}


def resolve(entry):
    """Accept a raw channel ID, an @handle, or any youtube.com URL form.
    Returns a channel ID or None. Costs 1 quota unit for anything but a raw ID."""
    e = entry.strip().rstrip("/")
    if e.startswith("UC") and len(e) == 24:
        return e
    if "youtube.com" in e or "youtu.be" in e:
        tail = e.split("youtube.com/")[-1].split("youtu.be/")[-1]
        if tail.startswith("channel/"):
            cid = tail.split("channel/")[1].split("/")[0].split("?")[0]
            return cid if cid.startswith("UC") else None
        for pre in ("c/", "user/", "@"):
            if tail.startswith(pre):
                e = ("@" + tail[len(pre):]) if pre != "@" else tail
                break
        else:
            e = "@" + tail.split("/")[0]
    e = e.split("?")[0].split("/")[0]
    if not e.startswith("@"):
        e = "@" + e
    r = get("/channels", {"part": "id", "forHandle": e})
    if r.get("items"):
        return r["items"][0]["id"]
    r = get("/channels", {"part": "id", "forUsername": e.lstrip("@")})
    if r.get("items"):
        return r["items"][0]["id"]
    return None


def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    # Strip inline comments so "UCxxxx  # Channel Name | 1,234 subs" works.
    raw = []
    for line in open(BASKET, encoding="utf-8"):
        entry = line.split("#")[0].strip()
        if entry:
            raw.append(entry)
    ids, unresolved, source = [], [], {}
    for entry in raw:
        cid = resolve(entry)
        if not cid:
            unresolved.append(entry)
        elif cid not in ids:
            ids.append(cid)
            source[cid] = entry
        else:
            print("  duplicate: %s -> %s (already in basket)" % (entry, cid))
    if unresolved:
        print("could not resolve %d entries:" % len(unresolved))
        for u in unresolved:
            print("   " + u)
    print("basket: %d channels, up to %d videos each" % (len(ids), PER_CHANNEL))

    channels = {}
    for i in range(0, len(ids), 50):
        for it in get("/channels", {"part": "snippet,statistics,contentDetails",
                                    "id": ",".join(ids[i:i + 50]),
                                    "maxResults": "50"}).get("items", []):
            s = it["statistics"]
            channels[it["id"]] = {
                "title": it["snippet"]["title"],
                "publishedAt": it["snippet"].get("publishedAt"),
                "subscriberCount": int(s.get("subscriberCount", 0)),
                "viewCount": int(s.get("viewCount", 0)),
                "videoCount": int(s.get("videoCount", 0)),
                "hiddenSubs": s.get("hiddenSubscriberCount", False),
                "uploads": it["contentDetails"]["relatedPlaylists"].get("uploads"),
                "source_entry": source.get(it["id"], it["id"]),
                "videos": {},
            }
    print("resolved %d/%d channels" % (len(channels), len(ids)))

    for n, (cid, ch) in enumerate(channels.items(), 1):
        vids, page = [], None
        while ch["uploads"] and len(vids) < PER_CHANNEL:
            p = {"part": "contentDetails", "playlistId": ch["uploads"],
                 "maxResults": "50"}
            if page:
                p["pageToken"] = page
            r = get("/playlistItems", p)
            vids += [i["contentDetails"]["videoId"] for i in r.get("items", [])]
            page = r.get("nextPageToken")
            if not page:
                break
        vids = vids[:PER_CHANNEL]
        for i in range(0, len(vids), 50):
            for it in get("/videos", {"part": "statistics,snippet,contentDetails",
                                      "id": ",".join(vids[i:i + 50])}).get("items", []):
                s = it["statistics"]
                ch["videos"][it["id"]] = {
                    "title": it["snippet"]["title"],
                    "publishedAt": it["snippet"]["publishedAt"],
                    "duration": it["contentDetails"]["duration"],
                    "viewCount": int(s.get("viewCount", 0)),
                    "likeCount": int(s.get("likeCount", 0)),
                    "commentCount": int(s.get("commentCount", 0)),
                }
        flag = "  <-- CHECK, low subs" if ch["subscriberCount"] < 100 else ""
        print("  %2d/%d %-28s subs=%-9s videos=%-4d from: %s%s"
              % (n, len(channels), ch["title"][:28],
                 "{:,}".format(ch["subscriberCount"]), len(ch["videos"]),
                 ch["source_entry"][:40], flag), flush=True)

    out = {"label": LABEL, "captured_at": now.isoformat(timespec="seconds"),
           "per_channel_cap": PER_CHANNEL,
           "unresolved": unresolved,
           "note": ("Public Data API values under the counting logic in force at "
                    "capture time. YouTube states the pre-2026-08-24 logic is not "
                    "retrievable from the public Data API afterwards."),
           "channels": channels}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w"), indent=1)
    tv = sum(c["viewCount"] for c in channels.values())
    nv = sum(len(c["videos"]) for c in channels.values())
    print("\nWROTE %s" % OUT)
    print("channels %d | videos captured %d | combined channel views {:,}".format(tv)
          % (len(channels), nv))


if __name__ == "__main__":
    main()
