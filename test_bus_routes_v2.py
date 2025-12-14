
import sys
import os

sys.path.append(os.getcwd())
from app.api.routes import load_data, BUS_STOPS

def test_bus_routes_loading():
    print("Loading data...")
    load_data()
    
    # Improved search for Majestic
    majestic = next((s for s in BUS_STOPS if "kempe" in s["name"].lower() and "gowda" in s["name"].lower()), None)
    
    if majestic:
        print(f"Majestic Stop found: '{majestic['name']}'")
        print(f"Routes Count: {len(majestic['routes'])}")
        print(f"Routes: {majestic['routes'][:20]}...")
    else:
        print("Majestic stop still not found.")

if __name__ == "__main__":
    test_bus_routes_loading()
