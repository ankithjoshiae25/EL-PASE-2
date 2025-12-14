import json
import os
import math
import csv
from datetime import datetime
from fastapi import APIRouter, Query, Body
from pydantic import BaseModel
from typing import List, Optional
import requests



def get_surge_multiplier():
    """
    Calculate price multiplier based on time of day.
    Morning Peak: 8 AM - 12 PM -> 1.4x
    Evening Peak: 5 PM - 9 PM -> 1.5x
    Late Night: 10 PM - 6 AM -> 1.2x
    Otherwise: 1.0x
    """
    now = datetime.now()
    hour = now.hour
    
    if 8 <= hour < 12:
        return 1.4
    elif 17 <= hour < 21:
        return 1.5
    elif hour >= 22 or hour < 6:
        return 1.2
    return 1.0


router = APIRouter()

# Mock Data for Locations (Bangalore)
LOCATIONS = {
    "koramangala": [12.9352, 77.6245],
    "whitefield": [12.9698, 77.7500],
    "indiranagar": [12.9784, 77.6408],
    "mg road": [12.9719, 77.6101],
    "electronic city": [12.8452, 77.6602],
    "hsr layout": [12.9121, 77.6446],
    "jayanagar": [12.9308, 77.5838],
    "banashankari": [12.9255, 77.5468],
    "malleswaram": [13.0031, 77.5643],
    "hebbal": [13.0334, 77.5891],
    "yelahanka": [13.1007, 77.5963],
    "majestic": [12.9767, 77.5713]
}

# Global Data Containers
METRO_STATIONS = []
METRO_LINES = []  # To store the actual line paths
BUS_STOPS = []
METRO_FARES = []
BUS_FARES = []

# Persistent User Weights (Simulated "AI Model")
USER_PROFILE_WEIGHTS = {
    "cab": 0.0,
    "auto": 0.0,
    "metro": 0.0,
    "bus": 0.0,
    "walk": 0.0
}
BUS_FARES = []

# Load Data on Startup
def load_data():
    global METRO_STATIONS, BUS_STOPS, METRO_LINES
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    
    # 1. Load Metro Data (GeoJSON)
    try:
        metro_path = os.path.join(base_path, "metro-lines-stations.geojson")
        with open(metro_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
            # First pass: Get Lines
            for feature in data["features"]:
                if feature["geometry"]["type"] == "LineString":
                    props = feature["properties"]
                    coords = feature["geometry"]["coordinates"]
                    # Normalize coords to [lat, lon] because GeoJSON is [lon, lat]
                    path_coords = [[c[1], c[0]] for c in coords]
                    
                    name = props.get("Name", "Unknown Line")
                    color = "purple" if "purple" in name.lower() or "line-1" in name.lower() else "green"
                    if "green" in name.lower() or "line-2" in name.lower():
                        color = "green"
                    
                    METRO_LINES.append({
                        "name": name,
                        "color": color,
                        "path": path_coords
                    })

            # Second pass: Get Stations and assign to lines
            for feature in data["features"]:
                if feature["geometry"]["type"] == "Point":
                    coords = feature["geometry"]["coordinates"] # [lon, lat]
                    lat, lon = coords[1], coords[0]
                    station_name = feature["properties"].get("Name", "Unknown Station")
                    
                    # Determine Line (Purple or Green) by checking proximity to lines
                    station_line = "Unknown"
                    min_dist_to_line = float('inf')
                    
                    for line in METRO_LINES:
                        # Check distance to nearest point on the line
                        for pt in line["path"]:
                            # Simple Euclidean approx is enough for assignment matching
                            d = (pt[0] - lat)**2 + (pt[1] - lon)**2
                            if d < min_dist_to_line:
                                min_dist_to_line = d
                                station_line = line["color"] # 'purple' or 'green'
                    
                    METRO_STATIONS.append({
                        "name": station_name,
                        "lon": lon,
                        "lat": lat,
                        "line": station_line
                    })
                    
        print(f"Loaded {len(METRO_STATIONS)} metro stations and {len(METRO_LINES)} metro lines.")
    except Exception as e:
        print(f"Error loading metro data: {e}")

    # 2. Load Bus Data (CSV)
    try:
        bus_path = os.path.join(base_path, "bmtc-bus-stops-2012.csv")
        with open(bus_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    # CSV Columns: "Bst_ID","NAME","Ward_No","X","Y"
                    name = row["NAME"]
                    lon = float(row["X"])
                    lat = float(row["Y"])
                    
                    # Note: This CSV does not contain route numbers, so we default to empty list
                    BUS_STOPS.append({
                        "name": name,
                        "lat": lat,
                        "lon": lon,
                        "routes": [] 
                    })
                except ValueError:
                    continue # Skip rows with invalid coords
                    
        print(f"Loaded {len(BUS_STOPS)} bus stops from CSV.")
    except Exception as e:
        print(f"Error loading bus data: {e}")

    # 3. Load Bus Fares (CSV)
    try:
        bus_fares_path = os.path.join(base_path, "bmtc_standard_fares.csv")
        with open(bus_fares_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    dist_str = row["Distance_km"]
                    fare = float(row["Fare_Rupees"])
                    
                    # Format "0-2", "2-4" -> take the upper bound
                    parts = dist_str.split('-')
                    if len(parts) == 2:
                        max_dist = float(parts[1])
                    else:
                        continue 
                    
                    BUS_FARES.append((max_dist, fare))
                except ValueError:
                    continue
            
        # Ensure fares are sorted by distance range
        BUS_FARES.sort(key=lambda x: x[0])
        print(f"Loaded {len(BUS_FARES)} bus fare ranges.")
    except Exception as e:
        print(f"Error loading bus fare data: {e}")

    # 4. Load Metro Fares (CSV)
    try:
        fares_path = os.path.join(base_path, "namma-metro-fares.csv")
        with open(fares_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    dist_str = row["Distance_km"]
                    fare = float(row["Fare_Rupees"])
                    
                    if "Above" in dist_str:
                        max_dist = float('inf')
                    else:
                        # Format "0-2", "2-4" -> take the upper bound
                        parts = dist_str.split('-')
                        if len(parts) == 2:
                            max_dist = float(parts[1])
                        else:
                            continue 
                    
                    METRO_FARES.append((max_dist, fare))
                except ValueError:
                    continue
            
        # Ensure fares are sorted by distance range
        METRO_FARES.sort(key=lambda x: x[0])
        print(f"Loaded {len(METRO_FARES)} fare ranges.")
    except Exception as e:
        print(f"Error loading fare data: {e}")

    # 5. Load Bus Routes Mapping (CSV)
    try:
        routes_path = os.path.join(base_path, "bus-route-num.csv.csv") # Note the double extension in file system
        if not os.path.exists(routes_path):
             routes_path = os.path.join(base_path, "bus-route-num.csv")
             
        with open(routes_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            
            # Create a lookup for stops to speed up matching
            # normalize name -> list of stop indices in BUS_STOPS
            stop_lookup = {}
            for i, stop in enumerate(BUS_STOPS):
                norm_name = stop["name"].lower().strip()
                if norm_name not in stop_lookup:
                    stop_lookup[norm_name] = []
                stop_lookup[norm_name].append(i)
            
            count_routes = 0
            for row in reader:
                route_num = row.get("Bus Route", "").strip()
                if not route_num: 
                    continue
                
                # Gather all "points" (Start, End, VIA)
                points = []
                if row.get("Starting From"): points.append(row["Starting From"])
                if row.get("Destination"): points.append(row["Destination"])
                if row.get("VIA"): points.extend(row["VIA"].split(','))
                
                # For each point, find matching bus stops
                for p in points:
                    p_clean = p.strip().lower()
                    if not p_clean: continue
                    
                    # Normalize for better matching (remove spaces, punctuation)
                    p_norm = p_clean.replace(" ", "").replace(".", "").replace("-", "")
                    
                    # Try exact match first (using lookup)
                    # We might need to map lookup keys to also be similarly normalized
                    
                    matched_indices = []
                    
                    # Heuristic matching against all stops
                    # This is O(N*M) but N=2000, M=~5 per route, so acceptable for startup
                    for idx, stop in enumerate(BUS_STOPS):
                        s_name = stop["name"].lower()
                        s_norm = s_name.replace(" ", "").replace(".", "").replace("-", "")
                        
                        # Check checks
                        # 1. Exact normalized match
                        if p_norm == s_norm:
                            matched_indices.append(idx)
                            continue
                            
                        # 2. Containment (one way or the other)
                        # p="magadi road" matches s="magadi road 5th cross"
                        # s="indiranagar" matches p="indiranagar police station"
                        if p_clean in s_name or s_name in p_clean:
                            matched_indices.append(idx)
                            continue
                        
                        # 3. Alias checks (Bus Stand <-> Station <-> TTMC)
                        s_alias = s_name.replace("bus stand", "station").replace("ttmc", "station")
                        p_alias = p_clean.replace("bus stand", "station").replace("ttmc", "station")
                        if p_alias in s_alias or s_alias in p_alias:
                             matched_indices.append(idx)
                             continue

                        # 4. Special case for Kempegowda / Majestic
                        if ("kempegowda" in p_norm or "majestic" in p_norm) and ("kempegowda" in s_norm or "majestic" in s_norm):
                             matched_indices.append(idx)
                             continue
                             
                    # Assign route to matched stops
                    for idx in matched_indices:
                        if route_num not in BUS_STOPS[idx]["routes"]:
                            BUS_STOPS[idx]["routes"].append(route_num)
                
                count_routes += 1
                
        print(f"Loaded routes for {len(BUS_STOPS)} stops from {count_routes} route definitions.")
    except Exception as e:
        print(f"Error loading bus route mapping: {e}")

load_data()

def get_coordinates(query):
    """Fetch coordinates from Nominatim API"""
    try:
        url = f"https://nominatim.openstreetmap.org/search?format=json&q={query}, Bangalore&limit=1"
        response = requests.get(url, headers={'User-Agent': 'LastMileApp/1.0'})
        data = response.json()
        if data:
            return [float(data[0]['lat']), float(data[0]['lon'])]
    except Exception as e:
        print(f"Geocoding error: {e}")
    return None

def calculate_distance(coord1, coord2):
    """Haversine formula for distance in km"""
    R = 6371  # Earth radius in km
    lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
    lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def find_nearest_station(lat, lon, stations):
    """Find the nearest station (metro or bus) to a given lat/lon"""
    if not stations:
        return None, None, float('inf')
    
    nearest_station = None
    min_dist = float('inf')
    
    for station in stations:
        dist = calculate_distance([lat, lon], [station["lat"], station["lon"]])
        if dist < min_dist:
            min_dist = dist
            nearest_station = station
            
    return nearest_station, [nearest_station["lat"], nearest_station["lon"]], min_dist

def get_metro_fare(distance_km):
    """Calculate metro fare based on distance"""
    for max_dist, fare in METRO_FARES:
        if distance_km <= max_dist:
            return fare
    # Default fallback if distance exceeds all ranges (though 'inf' handles this)
    return 90.0

def get_bus_fare(distance_km):
    """Calculate bus fare based on distance using BMTC standard fares"""
    for max_dist, fare in BUS_FARES:
        if distance_km <= max_dist:
            return fare
    # Default fallback if distance exceeds all ranges
    # Use the max known fare or a calculated estimate based on the highest rate
    if BUS_FARES:
        return BUS_FARES[-1][1]
    return 5 + (distance_km * 2) # Fallback to old linear formula if no data

@router.get("/metro-stations")
async def get_metro_stations():
    return {"stations": METRO_STATIONS}

@router.get("/metro-lines")
async def get_metro_lines():
    """Return the metro lines path data for visualization"""
    return {"lines": METRO_LINES}

@router.get("/bus-stops")
async def get_bus_stops():
    return {"stops": BUS_STOPS}

class UserPreference(BaseModel):
    priority: str
    mode: str
    maxWalk: str

@router.post("/train")
async def train_model(prefs: UserPreference):
    """
    Updates the weighting model based on user preferences.
    This simulates 'training' by adjusting the global scoring weights.
    """
    global USER_PROFILE_WEIGHTS
    
    print(f"Training model with preferences: {prefs}")
    
    # 1. Adjust based on declared Priority (Speed vs Cost)
    lr = 2.0 # Increased Learning Rate for immediate impact
    
    if prefs.priority == "speed":
        USER_PROFILE_WEIGHTS["cab"] += lr
        USER_PROFILE_WEIGHTS["auto"] += lr
        USER_PROFILE_WEIGHTS["metro"] += (lr * 0.5) # Metro is also fast
        USER_PROFILE_WEIGHTS["bus"] -= lr
        USER_PROFILE_WEIGHTS["walk"] -= lr
        
    elif prefs.priority == "cost":
        USER_PROFILE_WEIGHTS["bus"] += lr
        USER_PROFILE_WEIGHTS["walk"] += lr
        USER_PROFILE_WEIGHTS["metro"] += (lr * 0.5) # Metro is balanced
        USER_PROFILE_WEIGHTS["cab"] -= lr
        USER_PROFILE_WEIGHTS["auto"] -= (lr * 0.5)
        
    elif prefs.priority == "balanced":
         USER_PROFILE_WEIGHTS["metro"] += lr
         USER_PROFILE_WEIGHTS["auto"] += (lr * 0.2)
         USER_PROFILE_WEIGHTS["bus"] += (lr * 0.2)

    # 2. Adjust based on specific Mode Preference
    if prefs.mode != "any":
        # Boost the specific mode significantly
        # Map frontend values to keys
        key_map = {
            "namma_metro": "metro",
            "bmtc_bus": "bus",
            "cab": "cab",
            "auto": "auto",
            "walk": "walk"
        }
        # Handle 'metro' or 'namma_metro'
        target = next((v for k,v in key_map.items() if k in prefs.mode.lower() or prefs.mode.lower() in k), None)
        if target and target in USER_PROFILE_WEIGHTS:
             USER_PROFILE_WEIGHTS[target] += 1.0
             
    # Cap weights to avoid exploding scores
    for k in USER_PROFILE_WEIGHTS:
        USER_PROFILE_WEIGHTS[k] = max(-5.0, min(5.0, USER_PROFILE_WEIGHTS[k]))

    return {
        "status": "success", 
        "message": "Model weights updated based on feedback",
        "current_weights": USER_PROFILE_WEIGHTS
    }


def fetch_brouter_route(start_str, end_str, mode):
    """
    Fetch route from BRouter as fallback.
    start_str, end_str: "lon,lat"
    """
    profile = "trekking" if mode == "walking" else "car-fast"
    try:
        # BRouter expects lonlats=lon,lat|lon,lat
        url = f"https://brouter.de/brouter?lonlats={start_str}|{end_str}&profile={profile}&alternativeidx=0&format=geojson"
        response = requests.get(url, headers={'User-Agent': 'LastMileApp/1.0'}, timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"BRouter Error: {e}")
    return None

@router.get("/proxy/osrm")
async def get_osrm_route(
    start: str, 
    end: str, 
    mode: str = "driving"
):
    """
    Proxy OSRM requests with BRouter fallback.
    """
    # 1. Try OSRM
    try:
        if mode not in ["driving", "walking"]:
            mode = "driving"
            
        url = f"https://router.project-osrm.org/route/v1/{mode}/{start};{end}?overview=full&geometries=geojson"
        response = requests.get(url, headers={'User-Agent': 'LastMileApp/1.0'}, timeout=10) # Increased timeout
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"OSRM Primary Failed: {e}")

    # 2. Fallback to BRouter
    print("Trying BRouter Fallback...")
    brouter_data = fetch_brouter_route(start, end, mode)
    if brouter_data and "features" in brouter_data:
        coords = brouter_data["features"][0]["geometry"]["coordinates"]
        return {"routes": [{"geometry": {"coordinates": coords}}]}
            
    return {"error": "All routing services failed"}

@router.get("/autocomplete")
async def autocomplete(query: str = Query(..., min_length=2)):
    """
    Autocomplete search for locations, bus stops, and metro stations.
    Also falls back to Nominatim for broader search.
    """
    query = query.lower()
    results = []

    # 1. Search Known Locations
    for name, coords in LOCATIONS.items():
        if query in name:
            results.append({
                "name": name.title(),
                "type": "Location",
                "lat": coords[0],
                "lon": coords[1]
            })

    # 2. Search Metro Stations
    for station in METRO_STATIONS:
        if query in station["name"].lower():
            results.append({
                "name": station["name"],
                "type": "Metro Station",
                "lat": station["lat"],
                "lon": station["lon"]
            })

    # 3. Search Bus Stops (Limit to 5 matches to avoid bloat)
    bus_matches = 0
    for stop in BUS_STOPS:
        if query in stop["name"].lower():
            results.append({
                "name": stop["name"],
                "type": "Bus Stop",
                "lat": stop["lat"],
                "lon": stop["lon"]
            })
            bus_matches += 1
            if bus_matches >= 5:
                break

    # 4. External Nominatim Search (Bangalore context)
    # Only if local results are few
    if len(results) < 5:
        try:
            # Viewbox for Bangalore approx
            viewbox = "77.3,12.8,77.8,13.2" 
            url = f"https://nominatim.openstreetmap.org/search?format=json&q={query}&limit=5&viewbox={viewbox}&bounded=1"
            headers = {'User-Agent': 'LastMileApp/1.0'}
            response = requests.get(url, headers=headers, timeout=2)
            if response.status_code == 200:
                data = response.json()
                for item in data:
                    results.append({
                        "name": item['display_name'].split(',')[0], # Shorten name
                        "full_name": item['display_name'],
                        "type": "Address",
                        "lat": float(item['lat']),
                        "lon": float(item['lon'])
                    })
        except Exception as e:
            print(f"Autocomplete external error: {e}")

    # Remove duplicates based on name and roughly coords? 
    # For MVP, just return slice
    return {"results": results[:10]}

@router.get("/search")
async def search_routes(
    destination: str = Query(..., min_length=1), 
    start: str = Query("Indiranagar", min_length=1),
    s_lat: Optional[float] = None,
    s_lon: Optional[float] = None,
    d_lat: Optional[float] = None,
    d_lon: Optional[float] = None,
    preference: str = "balanced",
    mode_preference: str = "any",
    max_walk: str = "1.0"
):

    """
    Search for routes. Uses provided coordinates or geocodes the text.
    """
    # Resolve Start Coordinates
    if s_lat is not None and s_lon is not None:
        start_coords = [s_lat, s_lon]
    else:
        # Check known locations first
        start_coords = LOCATIONS.get(start.lower())
        if not start_coords:
            start_coords = get_coordinates(start)
            if not start_coords:
                start_coords = LOCATIONS.get("indiranagar")

    # Resolve Destination Coordinates
    if d_lat is not None and d_lon is not None:
        dest_coords = [d_lat, d_lon]
    else:
        # Check known locations first
        dest_coords = LOCATIONS.get(destination.lower())
        if not dest_coords:
            dest_coords = get_coordinates(destination)
            if not dest_coords:
                dest_coords = LOCATIONS.get("mg road")
            
    print(f"DEBUG: Start: {start_coords}, Dest: {dest_coords}")

    if not start_coords or not dest_coords:
        start_coords = start_coords or [12.9784, 77.6408]
        dest_coords = dest_coords or [12.9719, 77.6101]
    
    routes = []
            
    # Calculate Road Distance via OSRM

    def get_road_distance(coord1, coord2):
        """Fetch driving distance from OSRM, fallback to Haversine"""
        try:
            # OSRM expects lon,lat
            url = f"https://router.project-osrm.org/route/v1/driving/{coord1[1]},{coord1[0]};{coord2[1]},{coord2[0]}?overview=false"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("routes"):
                    # Distance is in meters, convert to km
                    return data["routes"][0]["distance"] / 1000
        except Exception as e:
            print(f"OSRM Distance Error: {e}")
        
        # Fallback 1: BRouter
        try:
            start_str = f"{coord1[1]},{coord1[0]}"
            end_str = f"{coord2[1]},{coord2[0]}"
            b_data = fetch_brouter_route(start_str, end_str, "driving")
            if b_data and "features" in b_data:
                props = b_data["features"][0]["properties"]
                # track-length is usually string in meters
                dist_m = float(props.get("track-length", 0))
                return dist_m / 1000
        except Exception as e:
            print(f"BRouter Distance Error: {e}")
        
        # Fallback: Haversine * 1.3
        return calculate_distance(coord1, coord2) * 1.3

    total_dist_km = get_road_distance(start_coords, dest_coords)
    
    # Find Nearest Metro Stations
    start_metro, start_metro_coords, start_metro_dist = find_nearest_station(start_coords[0], start_coords[1], METRO_STATIONS)
    end_metro, end_metro_coords, end_metro_dist = find_nearest_station(dest_coords[0], dest_coords[1], METRO_STATIONS)
    
    # Find Nearest Bus Stops
    start_bus, start_bus_coords, start_bus_dist = find_nearest_station(start_coords[0], start_coords[1], BUS_STOPS)
    end_bus, end_bus_coords, end_bus_dist = find_nearest_station(dest_coords[0], dest_coords[1], BUS_STOPS)

    metro_viable = False
    if start_metro and end_metro and start_metro != end_metro:
        if start_metro_dist < 5 and end_metro_dist < 5:
            metro_viable = True
            
    bus_viable = False
    common_routes = []
    start_bus_routes = []
    
    if start_bus and end_bus and start_bus != end_bus:
        start_routes = set(start_bus.get("routes", []))
        end_routes = set(end_bus.get("routes", []))
        common_routes = list(start_routes.intersection(end_routes))
        start_bus_routes = list(start_routes) # Fallback
        
        # Consider viable if close enough OR if we found a direct route
        if (start_bus_dist < 2 and end_bus_dist < 2) or common_routes:
             bus_viable = True

    # --- Route Generation ---

    # 1. Cab Direct (Grouped Options)
    
    # Calculate durations
    ride_duration = int(total_dist_km * 2.5) + 5
    ny_duration = int(total_dist_km * 3.0) + 5 
    
    # Feature: Dynamic Surge Pricing
    surge_multiplier = get_surge_multiplier()

    # Calculate Costs (Revised for realism)
    # Base Costs
    uber_cost_base = 50 + (19 * total_dist_km) + (2 * ride_duration)
    ola_cost_base = 60 + (21 * total_dist_km) + (2.2 * ride_duration)
    
    ny_cost_base = 30 + (15 * total_dist_km) + (1.5 * ny_duration)
    uber_auto_base = 25 + (10 * total_dist_km) + (0.5 * ny_duration)
    ola_auto_base = 25 + (11 * total_dist_km) + (0.5 * ny_duration)
    
    # Apply Surge
    uber_cost = int(uber_cost_base * surge_multiplier)
    ola_cost = int(ola_cost_base * surge_multiplier)
    ny_cost = int(ny_cost_base * surge_multiplier)
    uber_auto_cost = int(uber_auto_base * surge_multiplier)
    ola_auto_cost = int(ola_auto_base * surge_multiplier)

    # Correct short distance pricing (Minimum fares)
    if uber_cost < 80: uber_cost = 80
    if ola_cost < 80: ola_cost = 80
    if ny_cost < 40: ny_cost = 40
    if uber_auto_cost < 50: uber_auto_cost = 50
    if ola_auto_cost < 50: ola_auto_cost = 50

    # Find cheapest for display
    min_cab_cost = min(uber_cost, ola_cost, ny_cost, uber_auto_cost, ola_auto_cost)
    
    routes.append({
        "id": 1,
        "mode": "Cab Direct",
        "duration": ride_duration,
        "cost": min_cab_cost, # Display cheapest "From X"
        "safety": "High",
        "ai_score": 9.0, 
        "details": "Uber, Ola, Namma Yatri",
        "sub_options": [
            {"name": "Namma Yatri (Auto)", "cost": ny_cost, "duration": ny_duration},
            {"name": "Uber (Auto)", "cost": uber_auto_cost, "duration": ny_duration},
            {"name": "Ola (Auto)", "cost": ola_auto_cost, "duration": ny_duration},
            {"name": "Uber (Car)", "cost": uber_cost, "duration": ride_duration},
            {"name": "Ola (Car)", "cost": ola_cost, "duration": ride_duration}
        ],
        "segments": [{
            "mode": "cab",
            "from": start_coords,
            "to": dest_coords,
            "instruction": "Cab Direct to destination",
            "identifier": "Cab/Auto"
        }]
    })

    # 2. Metro Options (Expanded with Auto/Walk variants)
    if start_metro and end_metro and start_metro["name"] != end_metro["name"]:
        
        # Metro core stats
        metro_ride_dist = calculate_distance([start_metro["lat"], start_metro["lon"]], [end_metro["lat"], end_metro["lon"]]) * 1.2
        metro_fare = get_metro_fare(metro_ride_dist)
        metro_dur = int(metro_ride_dist * 2.2) + 6

        # --- Variant A: Metro + Best Connection (Existing Logic - mostly walk if close) ---
        leg1_mode = "walk" if start_metro_dist < 1.5 else "auto"
        leg3_mode = "walk" if end_metro_dist < 1.5 else "auto"
        
        # Calculate Variant A
        if leg1_mode == "auto":
             leg1_dur = int(start_metro_dist * 3 + 5)
             leg1_cost = int(25 + (10 * start_metro_dist) + (0.5 * leg1_dur))
             if leg1_cost < 30: leg1_cost = 30
        else:
             leg1_dur = int(start_metro_dist * 12)
             leg1_cost = 0

        leg3_cost = 0
        if leg3_mode == "auto":
             leg3_dur = int(end_metro_dist * 3 + 5)
             leg3_cost = int(25 + (10 * end_metro_dist) + (0.5 * leg3_dur))
             if leg3_cost < 30: leg3_cost = 30
        else:
             leg3_dur = int(end_metro_dist * 12)

        total_cost_a = leg1_cost + metro_fare + leg3_cost
        total_dur_a = leg1_dur + metro_dur + leg3_dur

        routes.append({
            "id": 3,
            "mode": f"Metro + {leg1_mode.title()}/{leg3_mode.title()}",
            "duration": int(total_dur_a),
            "cost": int(total_cost_a),
            "safety": "High",
            "ai_score": 8.8,
            "details": f"Via {start_metro['name']} & {end_metro['name']}",
            "sub_costs": {
                "leg1_auto": leg1_cost if leg1_mode == "auto" else 0,
                "leg3_auto": leg3_cost if leg3_mode == "auto" else 0,
                "metro": metro_fare
            },
            "segments": [
                {
                    "mode": leg1_mode,
                    "from": start_coords,
                    "to": [start_metro["lat"], start_metro["lon"]],
                    "instruction": f"{leg1_mode.title()} to {start_metro['name']}",
                    "identifier": f"{round(start_metro_dist, 1)} km"
                },
                {
                    "mode": "metro",
                    "from": [start_metro["lat"], start_metro["lon"]],
                    "to": [end_metro["lat"], end_metro["lon"]],
                    "instruction": f"Metro to {end_metro['name']}",
                    "identifier": "Purple/Green Line",
                    "line_color": start_metro.get("line", "purple") 
                },
                {
                    "mode": leg3_mode,
                    "from": [end_metro["lat"], end_metro["lon"]],
                    "to": dest_coords,
                    "instruction": f"{leg3_mode.title()} to Destination",
                    "identifier": f"{round(end_metro_dist, 1)} km"
                }
            ]
        })

        # --- Variant B: Metro + Auto (Explicit, even if close) ---
        # Generate this ONLY if Variant A wasn't fully Auto and distance is > 0.5km (to avoid absurd short autos)
        if (leg1_mode == "walk" and start_metro_dist > 0.5) or (leg3_mode == "walk" and end_metro_dist > 0.5):
            
            # Recalculate for Forced Auto
            leg1_dur_b = int(start_metro_dist * 3 + 5)
            leg1_cost_b = int(25 + (10 * start_metro_dist) + (0.5 * leg1_dur_b))
            if leg1_cost_b < 30: leg1_cost_b = 30
            
            leg3_dur_b = int(end_metro_dist * 3 + 5)
            leg3_cost_b = int(25 + (10 * end_metro_dist) + (0.5 * leg3_dur_b))
            if leg3_cost_b < 30: leg3_cost_b = 30
            
            total_cost_b = leg1_cost_b + metro_fare + leg3_cost_b
            total_dur_b = leg1_dur_b + metro_dur + leg3_dur_b
            
            routes.append({
                "id": 6,
                "mode": "Metro + Auto (Comfort)",
                "duration": int(total_dur_b),
                "cost": int(total_cost_b),
                "safety": "High",
                "ai_score": 8.6,
                "details": "Avoid walking",
                "sub_costs": {
                    "leg1_auto": leg1_cost_b,
                    "leg3_auto": leg3_cost_b,
                    "metro": metro_fare
                },
                "segments": [
                    {
                        "mode": "auto",
                        "from": start_coords,
                        "to": [start_metro["lat"], start_metro["lon"]],
                        "instruction": f"Auto to {start_metro['name']}",
                        "identifier": f"₹{leg1_cost_b}"
                    },
                    {
                        "mode": "metro",
                        "from": [start_metro["lat"], start_metro["lon"]],
                        "to": [end_metro["lat"], end_metro["lon"]],
                        "instruction": f"Metro to {end_metro['name']}",
                        "identifier": "Purple/Green Line",
                        "line_color": start_metro.get("line", "purple") 
                    },
                    {
                        "mode": "auto",
                        "from": [end_metro["lat"], end_metro["lon"]],
                        "to": dest_coords,
                        "instruction": f"Auto to Destination",
                        "identifier": f"₹{leg3_cost_b}"
                    }
                ]
            })

    # 4. Bus - Optimization for Cost
    if bus_viable:
        if common_routes:
            bus_route_ids = common_routes[:3]
            bus_route_display = ", ".join(bus_route_ids)
            instruction_text = f"Take Bus {bus_route_display}"
            details_text = f"Direct Bus {bus_route_display}"
        elif start_bus_routes:
             bus_route_ids = start_bus_routes[:3]
             bus_route_display = ", ".join(bus_route_ids)
             instruction_text = f"Take Bus {bus_route_display}..."
             details_text = f"Bus {bus_route_display}... (Check at stop)"
        else:
             bus_route_display = "Any Bus"
             instruction_text = "Take Bus towards destination"
             details_text = "Standard Bus Service"

        routes.append({
            "id": 4,
            "mode": "Bus + Walk",
            "duration": int(total_dist_km * 3.5) + 15, 
            "cost": int(get_bus_fare(total_dist_km)), 
            "safety": "Medium",
            "ai_score": 8.0 if common_routes else 7.0,
            "details": details_text,
            "segments": [
                {
                    "mode": "walk", 
                    "from": start_coords, 
                    "to": start_bus_coords,
                    "instruction": f"Walk to {start_bus['name']}",
                    "identifier": f"{round(start_bus_dist, 1)} km"
                },
                {
                    "mode": "bus", 
                    "from": start_bus_coords, 
                    "to": end_bus_coords,
                    "instruction": instruction_text,
                    "identifier": bus_route_display,
                    "from_stop": start_bus['name'],
                    "to_stop": end_bus['name']
                },
                {
                    "mode": "walk", 
                    "from": end_bus_coords, 
                    "to": dest_coords,
                    "instruction": f"Walk to {destination}",
                    "identifier": f"{round(end_bus_dist, 1)} km"
                }
            ]
        })

    # --- Scoring & Sorting ---
    for r in routes:
        score = r["ai_score"]
        
        # 1. Apply User "Trained" Profile Weights
        # Check which modes are present in this route
        route_mode_str = r["mode"].lower()
        
        if "cab" in route_mode_str or "uber" in route_mode_str or "ola" in route_mode_str:
            score += USER_PROFILE_WEIGHTS["cab"]
            
        if "auto" in route_mode_str or "namma yatri" in route_mode_str:
            score += USER_PROFILE_WEIGHTS["auto"]
            
        if "metro" in route_mode_str:
            score += USER_PROFILE_WEIGHTS["metro"]
            
        if "bus" in route_mode_str:
            score += USER_PROFILE_WEIGHTS["bus"]
            
        if "walk" in route_mode_str:
             score += USER_PROFILE_WEIGHTS["walk"]

        # 2. Hard Priority Adjustment (Legacy - kept for baseline behavior)
        if preference == "speed":
            if "Cab" in r["mode"] or "Uber" in r["mode"] or "Ola" in r["mode"]:
                score += 3.0
            elif "Auto" in r["mode"] or "Namma Yatri" in r["mode"]:
                score += 2.0
            else:
                score -= 2.0 
                
        elif preference == "cost":
            if "Bus" in r["mode"]:
                score += 3.0
            elif "Metro" in r["mode"] and "Walk" in r["mode"]: 
                score += 2.0
            else:
                score -= 2.0
                
        elif preference == "balanced":
             if "Metro" in r["mode"]:
                 score += 3.0
             elif "Auto" in r["mode"] or "Namma Yatri" in r["mode"] or "Bus" in r["mode"]:
                 score += 1.0 
             else:
                 score -= 1.0

        r["ai_score"] = round(max(1.0, min(10.0, score)), 1)

    routes.sort(key=lambda x: x["ai_score"], reverse=True)

    
    for r in routes:
        seg_modes = [s["mode"] for s in r.get("segments", [])]
        print(f"DEBUG ROUTE: ID={r.get('id')} Mode={r['mode']} Segments={seg_modes}")

    return {
        "start": start,
        "start_coords": start_coords,
        "destination": destination,
        "destination_coords": dest_coords,
        "total_distance_km": round(total_dist_km, 2),
        "routes": routes
    }
