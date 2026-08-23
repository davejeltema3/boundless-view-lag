import json, os, sys, datetime, urllib.request, urllib.parse, urllib.error
DATA_API="https://www.googleapis.com/youtube/v3"
AN="https://youtubeanalytics.googleapis.com/v2/reports"
c=json.load(open("/mnt/user-data/uploads/Boundless Content/Shared Files/credentials/youtube-oauth.json"))
d=urllib.parse.urlencode({"client_id":c["client_id"],"client_secret":c["client_secret"],
 "refresh_token":c["refresh_token"],"grant_type":"refresh_token"}).encode()
AT=json.load(urllib.request.urlopen(urllib.request.Request("https://oauth2.googleapis.com/token",d)))["access_token"]
def get(url,p):
    u=url+"?"+urllib.parse.urlencode(p)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(u,headers={"Authorization":"Bearer "+AT}),timeout=40) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            print("HTTP",e.code,e.read().decode()[:200]); return {}
        except Exception as ex:
            if attempt==2: print("fail",ex); return {}
def an(metrics,dimensions,start,end,**kw):
    p={"ids":"channel==MINE","startDate":start,"endDate":end,"metrics":metrics,"dimensions":dimensions}
    p.update({k:v for k,v in kw.items() if v})
    return get(AN,p).get("rows",[])

now=datetime.datetime.now(datetime.timezone.utc); today=now.date()
START="2015-01-01"; END=today.isoformat()
LABEL=os.environ.get("LABEL","pre"); TOP_N=int(os.environ.get("TOP_N","20"))

ch=get(DATA_API+"/channels",{"part":"contentDetails,statistics","mine":"true"})["items"][0]
up=ch["contentDetails"]["relatedPlaylists"]["uploads"]
ids=[];page=None
while True:
    p={"part":"contentDetails","playlistId":up,"maxResults":"50"}
    if page:p["pageToken"]=page
    r=get(DATA_API+"/playlistItems",p)
    ids+=[i["contentDetails"]["videoId"] for i in r.get("items",[])]
    page=r.get("nextPageToken")
    if not page:break
print("catalog:",len(ids),"videos",flush=True)

public={}
for i in range(0,len(ids),50):
    for it in get(DATA_API+"/videos",{"part":"statistics,snippet,contentDetails","id":",".join(ids[i:i+50])}).get("items",[]):
        s=it["statistics"]
        public[it["id"]]={"title":it["snippet"]["title"],"publishedAt":it["snippet"]["publishedAt"],
          "duration":it["contentDetails"]["duration"],"viewCount":int(s.get("viewCount",0)),
          "likeCount":int(s.get("likeCount",0)),"commentCount":int(s.get("commentCount",0))}
print("public counters:",len(public),flush=True)

life={}
for row in an("views,engagedViews,averageViewPercentage,averageViewDuration,estimatedMinutesWatched",
              "video",START,END,sort="-views",maxResults="200"):
    life[row[0]]={"views":row[1],"engagedViews":row[2],"avgViewPct":row[3],"avgDuration":row[4],"minutes":row[5]}
print("lifetime analytics:",len(life),flush=True)

top=[v for v,_ in sorted(life.items(),key=lambda kv:-kv[1]["views"])[:TOP_N]]
curves={}
for n,vid in enumerate(top,1):
    rows=an("audienceWatchRatio,relativeRetentionPerformance","elapsedVideoTimeRatio",START,END,filters="video=="+vid)
    if rows: curves[vid]=[[round(r[0],2),round(r[1],4),round(r[2],4)] for r in rows]
    print("  curve %d/%d %s %s"%(n,len(top),vid,"ok" if rows else "empty"),flush=True)

splits={}
for dim in ("insightTrafficSourceType","deviceType","subscribedStatus"):
    for w,s0 in (("lifetime",START),("last90",(today-datetime.timedelta(days=90)).isoformat())):
        splits["%s_%s"%(dim,w)]=[list(r) for r in an("views,engagedViews",dim,s0,END,sort="-views")]
print("splits:",len(splits),flush=True)

out={"label":LABEL,"captured_at":now.isoformat(timespec="seconds"),
 "note":("Public viewCount values use the counting logic in force at capture time. "
         "YouTube states the pre-2026-08-24 logic is not retrievable from the public "
         "Data API after the switch."),
 "channel_public":{k:int(v) for k,v in ch["statistics"].items() if str(v).isdigit()},
 "video_count":len(ids),"top_n":TOP_N,"public":public,"lifetime_analytics":life,
 "retention_curves":curves,"splits":splits}
open("catalog_%s.json"%LABEL,"w").write(json.dumps(out,indent=1))
print("\nWROTE catalog_%s.json"%LABEL)
print("total public views: {:,}".format(sum(v["viewCount"] for v in public.values())))
print("curves:",len(curves),"| lifetime rows:",len(life))
