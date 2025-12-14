
import sys
import os

sys.path.append(os.getcwd())
from app.api.routes import load_data, find_nearest_station, BUS_STOPS, LOCATIONS

def debug_specific_route():
    print("Loading data...")
    load_data()
    
    # Test Case 1: Indiranagar to MG Road
    l1 = LOCATIONS["indiranagar"]
    l2 = LOCATIONS["mg road"]
    
    s1, _, _ = find_nearest_station(l1[0], l1[1], BUS_STOPS)
    s2, _, _ = find_nearest_station(l2[0], l2[1], BUS_STOPS)
    
    print(f"\n--- Indiranagar to MG Road ---")
    print(f"Start: {s1['name']} (Routes: {len(s1['routes'])}) -> {s1['routes'][:5]}")
    print(f"End: {s2['name']} (Routes: {len(s2['routes'])}) -> {s2['routes'][:5]}")
    
    common = set(s1['routes']).intersection(set(s2['routes']))
    print(f"Common: {common}")
    
    # Test Case 2: Koramangala to Majestic
    print(f"\n--- Koramangala to Majestic ---")
    l3 = LOCATIONS["koramangala"]
    l4 = LOCATIONS["majestic"]
    
    s3, _, _ = find_nearest_station(l3[0], l3[1], BUS_STOPS)
    s4, _, _ = find_nearest_station(l4[0], l4[1], BUS_STOPS)
    
    print(f"Start: {s3['name']} (Routes: {len(s3['routes'])}) -> {s3['routes'][:5]}")
    print(f"End: {s4['name']} (Routes: {len(s4['routes'])}) -> {s4['routes'][:5]}")
    
    common2 = set(s3['routes']).intersection(set(s4['routes']))
    print(f"Common: {common2}")

if __name__ == "__main__":
    debug_specific_route()
