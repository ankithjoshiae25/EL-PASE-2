import json
import os
import math
import csv
from fastapi import APIRouter, Query
from typing import List, Optional
import requests

router = APIRouter()

# Mock Data for Locations (Bangalore)
LOCATIONS = {
    "koramangala": [12.9352, 77.6245],
    "whitefield": [12.9698, 77.7500],
    "indiranagar": [12.9784, 77.6408],
    "mg road": [12.9719, 77.6101],
    "electronic city": [12.8452, 77.6602],
    "hsr layout": [12.9121, 77.6446]
}

# Global Data Containers
METRO_STATIONS = []
BUS_STOPS = []

# Load Data on Startup
def load_data():
    global METRO_STATIONS, BUS_STOPS
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    
    # 1. Load Metro Data (GeoJSON)
    try:
        metro_path = os.path.join(base_path, "metro-lines-stations.geojson")
        with open(metro_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for feature in data["features"]:
                if feature["geometry"]["type"] == "Point":
                    coords = feature["geometry"]["coordinates"]
                    METRO_STATIONS.append({
                        "name": feature["properties"].get("Name", "Unknown Station"),
                        "lon": coords[0],
                        "lat": coords[1]
                    })
        print(f"Loaded {len(METRO_STATIONS)} metro stations.")
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

load_data()

def get_coordinates(query):
    """Fetch coordinates from Nominatim API"""
    try:
        url = f"https://nominatim.openstreetmap.org/search?format=json&q={query}&limit=1"
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

@router.get("/metro-stations")
async def get_metro_stations():
    return {"stations": METRO_STATIONS}

@router.get("/bus-stops")
async def get_bus_stops():
    return {"stops": BUS_STOPS}

@router.get("/search")
async def search_routes(
    destination: str = Query(..., min_length=1), 
    start: str = Query("Indiranagar", min_length=1),
    s_lat: Optional[float] = None,
    s_lon: Optional[float] = None,
    d_lat: Optional[float] = None,
    d_lon: Optional[float] = None
):
    """
    Search for routes. Uses provided coordinates or geocodes the text.
    """
    # Resolve Start Coordinates
    if s_lat is not None and s_lon is not None:
        start_coords = [s_lat, s_lon]
    else:
        start_coords = get_coordinates(start)
        if not start_coords:
            start_coords = LOCATIONS.get(start.lower()) or LOCATIONS.get("indiranagar")

    # Resolve Destination Coordinates
    if d_lat is not None and d_lon is not None:
        dest_coords = [d_lat, d_lon]
    else:
        dest_coords = get_coordinates(destination)
        if not dest_coords:
            dest_coords = LOCATIONS.get(destination.lower()) or LOCATIONS.get("mg road")
            
    print(f"DEBUG: Start: {start_coords}, Dest: {dest_coords}")

    if not start_coords or not dest_coords:
        start_coords = start_coords or [12.9784, 77.6408]
        dest_coords = dest_coords or [12.9719, 77.6101]
            
    # Calculate Road Distance via OSRM
    def get_road_distance(coord1, coord2):
        """Fetch driving distance from OSRM, fallback to Haversine"""
        try:
            # OSRM expects lon,lat
            url = f"http://router.project-osrm.org/route/v1/driving/{coord1[1]},{coord1[0]};{coord2[1]},{coord2[0]}?overview=false"
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                data = response.json()
                if data.get("routes"):
                    # Distance is in meters, convert to km
                    return data["routes"][0]["distance"] / 1000
        except Exception as e:
            print(f"OSRM Distance Error: {e}")
        
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
    if start_bus and end_bus and start_bus != end_bus:
        if start_bus_dist < 2 and end_bus_dist < 2: # Bus stops usually closer
            bus_viable = True
            # Check for common routes
            start_routes = set(start_bus.get("routes", []))
            end_routes = set(end_bus.get("routes", []))
            common_routes = list(start_routes.intersection(end_routes))

    # Generate intermediate points based on direction (for non-metro routes)
    def get_waypoint(start, end, progress):
        return [
            start[0] + (end[0] - start[0]) * progress,
            start[1] + (end[1] - start[1]) * progress
        ]

    mid_point = get_waypoint(start_coords, dest_coords, 0.5)
    
    # Use actual metro station coords if viable, else mock fallback
    q1_point = start_metro_coords if metro_viable else get_waypoint(start_coords, dest_coords, 0.25)
    q3_point = end_metro_coords if metro_viable else get_waypoint(start_coords, dest_coords, 0.75)
    
    start_metro_name = start_metro["name"] if metro_viable else "Station A"
    end_metro_name = end_metro["name"] if metro_viable else "Station B"

    routes = [
        {
            "id": 1,
            "mode": "Uber Moto",
            "duration": int(total_dist_km * 3) + 5, # Approx 20km/h avg + buffer
            "cost": int(25 + (total_dist_km * 10)),
            "safety": "Medium",
            "ai_score": 8.5,
            "details": "Fastest in traffic",
            "segments": [
                {
                    "mode": "moto", 
                    "from": start_coords, 
                    "to": dest_coords,
                    "instruction": f"Ride Uber Moto directly to {destination}",
                    "identifier": "KA-01-EQ-1234"
                }
            ]
        }
    ]

    if metro_viable:
        routes.append({
            "id": 3,
            "mode": "Metro + Walk",
            "duration": int(total_dist_km * 2.5) + 15,
            "cost": int(10 + (total_dist_km * 4)),
            "safety": "High",
            "ai_score": 9.2,
            "details": f"Via {start_metro_name}",
            "segments": [
                {
                    "mode": "walk", 
                    "from": start_coords, 
                    "to": q1_point,
                    "instruction": f"Walk to {start_metro_name}",
                    "identifier": f"{round(start_metro_dist, 1)} km"
                },
                {
                    "mode": "metro", 
                    "from": q1_point, 
                    "to": q3_point,
                    "instruction": f"Metro to {end_metro_name}",
                    "identifier": "Purple/Green Line",
                    "from_stop": start_metro_name,
                    "to_stop": end_metro_name
                },
                {
                    "mode": "walk", 
                    "from": q3_point, 
                    "to": dest_coords,
                    "instruction": f"Walk to {destination}",
                    "identifier": f"{round(end_metro_dist, 1)} km"
                }
            ]
        })
        
        routes.append({
            "id": 4,
            "mode": "Auto + Metro + Auto",
            "duration": int(total_dist_km * 2) + 10,
            "cost": int(40 + (total_dist_km * 8)),
            "safety": "High",
            "ai_score": 8.8,
            "details": "Comfortable & Fast",
            "segments": [
                {
                    "mode": "auto", 
                    "from": start_coords, 
                    "to": q1_point,
                    "instruction": f"Take Auto to {start_metro_name}",
                    "identifier": "Uber Auto"
                },
                {
                    "mode": "metro", 
                    "from": q1_point, 
                    "to": q3_point,
                    "instruction": f"Metro to {end_metro_name}",
                    "identifier": "Metro",
                    "from_stop": start_metro_name,
                    "to_stop": end_metro_name
                },
                {
                    "mode": "auto", 
                    "from": q3_point, 
                    "to": dest_coords,
                    "instruction": f"Take Auto to {destination}",
                    "identifier": "Ola Auto"
                }
            ]
        })
    
    if bus_viable:
        bus_route_id = common_routes[0] if common_routes else "Any Bus"
        bus_instruction = f"Take Bus {bus_route_id}" if common_routes else "Take Bus towards destination"
        
        routes.append({
            "id": 5,
            "mode": "Bus + Walk",
            "duration": int(total_dist_km * 3.5) + 15, 
            "cost": int(5 + (total_dist_km * 2)), # Very cheap
            "safety": "Medium",
            "ai_score": 8.0 if common_routes else 7.5,
            "details": f"Via {start_bus['name']}",
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
                    "instruction": bus_instruction,
                    "identifier": bus_route_id,
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
    else:
        # Fallback generic bus route
        routes.append({
            "id": 5,
            "mode": "Cab + Bus + Walk",
            "duration": int(total_dist_km * 4) + 10, 
            "cost": int(30 + (total_dist_km * 5)),
            "safety": "Medium",
            "ai_score": 6.5,
            "details": "Budget friendly long haul",
            "segments": [
                {
                    "mode": "cab", 
                    "from": start_coords, 
                    "to": mid_point,
                    "instruction": "Take Cab to Bus Stop",
                    "identifier": "Uber Go"
                },
                {
                    "mode": "bus", 
                    "from": mid_point, 
                    "to": q3_point,
                    "instruction": "Take Bus towards Destination",
                    "identifier": "BMTC",
                    "from_stop": "Stop A",
                    "to_stop": "Stop B"
                },
                {
                    "mode": "walk", 
                    "from": q3_point, 
                    "to": dest_coords,
                    "instruction": "Walk to destination",
                    "identifier": "400m"
                }
            ]
        })
    
    # Sort by AI Score descending
    routes.sort(key=lambda x: x["ai_score"], reverse=True)
    
    return {
        "start": start,
        "start_coords": start_coords,
        "destination": destination,
        "destination_coords": dest_coords,
        "total_distance_km": round(total_dist_km, 2),
        "routes": routes
    }
