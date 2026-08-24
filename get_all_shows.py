import urllib.request, json
shows = json.loads(urllib.request.urlopen("https://ticketsphere-api-ypje.onrender.com/api/shows/").read())
for s in shows:
    print(f"ID: {s['id']}, Venue: {s['venue_name']}, Seats: {s['total_seats']}")
