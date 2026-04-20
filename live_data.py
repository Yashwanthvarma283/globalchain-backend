import httpx
import asyncio
import time
from typing import Dict, Any

# Simple In-Memory Cache to respect API Rate Limits
cache = {
    "data": None,
    "timestamp": 0
}
CACHE_TTL = 300 # 5 minutes

async def fetch_usgs(client: httpx.AsyncClient):
    try:
        res = await client.get("https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson", timeout=10.0)
        res.raise_for_status()
        data = res.json()
        disasters = []
        for feature in data.get("features", [])[:15]: # Keep up to 15
            coords = feature["geometry"]["coordinates"] # [lng, lat, depth]
            disasters.append({
                "lat": coords[1],
                "lng": coords[0],
                "title": feature["properties"]["title"],
                "type": "natural"
            })
        return disasters
    except Exception as e:
        print(f"USGS Fetch Error: {e}")
        return []

async def fetch_reliefweb(client: httpx.AsyncClient):
    # Known active conflict zones as reliable fallback data
    KNOWN_CONFLICTS = [
        {"lat": 48.3794,  "lng": 31.1656,  "title": "Ukraine – Russia Armed Conflict", "type": "geopolitical"},
        {"lat": 31.0461,  "lng": 34.8516,  "title": "Gaza – Israel Armed Conflict",    "type": "geopolitical"},
        {"lat": 15.5527,  "lng": 48.5164,  "title": "Yemen Civil War",                 "type": "geopolitical"},
        {"lat": 15.3694,  "lng": 38.9318,  "title": "Ethiopia – Tigray Conflict",      "type": "geopolitical"},
        {"lat": 12.8628,  "lng": 30.2176,  "title": "Sudan Armed Conflict",            "type": "geopolitical"},
        {"lat": 33.8869,  "lng": 35.8623,  "title": "Lebanon Border Tensions",         "type": "geopolitical"},
        {"lat": 4.8594,   "lng": 31.5713,  "title": "South Sudan Civil Unrest",        "type": "geopolitical"},
        {"lat": -4.0383,  "lng": 21.7587,  "title": "DRC Eastern Conflict",            "type": "geopolitical"},
    ]
    try:
        url = "https://api.reliefweb.int/v1/reports?appname=globalchain&query[value]=armed+conflict&query[operator]=AND&filter[field]=type.name&filter[value]=Situation+Report&limit=10&fields[include][]=title&fields[include][]=country&fields[include][]=primary_country"
        res = await client.get(url, timeout=12.0)
        res.raise_for_status()
        data = res.json()
        api_conflicts = []
        for item in data.get("data", []):
            fields = item.get("fields", {})
            country = fields.get("primary_country", {})
            location = country.get("location")
            if location and location.get("lat") and location.get("lon"):
                api_conflicts.append({
                    "lat": location.get("lat"),
                    "lng": location.get("lon"),
                    "title": fields.get("title", "Active Conflict")[:80],
                    "type": "geopolitical"
                })
        # Merge API results with known conflicts (deduplicated)
        final = {c["title"]: c for c in KNOWN_CONFLICTS}
        for c in api_conflicts:
            final[c["title"]] = c
        return list(final.values())
    except Exception as e:
        print(f"ReliefWeb Fetch Error: {e}, using known conflict fallback")
        return KNOWN_CONFLICTS

async def fetch_opensky(client: httpx.AsyncClient):
    try:
        res = await client.get("https://opensky-network.org/api/states/all", timeout=10.0)
        res.raise_for_status()
        data = res.json()
        traffic = []
        states = data.get("states", [])
        if states:
            # We just grab up to 50 active flights randomly scattered that have coordinates
            for state in states[:150]:
                lng = state[5]
                lat = state[6]
                if lat is not None and lng is not None:
                    traffic.append({
                        "id": state[0],
                        "lat": lat,
                        "lng": lng
                    })
                    if len(traffic) >= 50:
                        break
        return traffic
    except Exception as e:
        print(f"OpenSky Fetch Error: {e}")
        # Fallback simulated traffic hubs to ensure app never breaks
        return [
            {"id":"sim1", "lat": 40.71, "lng": -74.00},
            {"id":"sim2", "lat": 51.50, "lng": -0.12},
            {"id":"sim3", "lat": 22.54, "lng": 114.05}
        ]

async def update_live_status() -> Dict[str, Any]:
    global cache
    
    if time.time() - cache["timestamp"] < CACHE_TTL and cache["data"] is not None:
        return cache["data"]

    async with httpx.AsyncClient() as client:
        disasters, conflicts, traffic = await asyncio.gather(
            fetch_usgs(client),
            fetch_reliefweb(client),
            fetch_opensky(client)
        )

    result = {
        "disasters": disasters,
        "conflicts": conflicts,
        "traffic": traffic,
        "status": "NOMINAL" if len(disasters) < 10 else "ELEVATED RISK"
    }
    
    cache["data"] = result
    cache["timestamp"] = time.time()
    
    return result
