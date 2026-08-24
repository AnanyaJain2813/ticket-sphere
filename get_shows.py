import urllib.request, json
shows = json.loads(urllib.request.urlopen("https://ticketsphere-api-ypje.onrender.com/api/shows/").read())
for s in shows:
    if "ICON IMAX" in s["venue_name"]:
        print(s["id"])
