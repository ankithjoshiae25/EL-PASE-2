
import sys
import os

# Add the current directory to sys.path so we can import app
sys.path.append(os.getcwd())

from app.api.routes import load_data, BUS_STOPS

def test_bus_routes_loading():
    print("Loading data...")
    load_data()
    print(f"Total Bus Stops: {len(BUS_STOPS)}")
    
    stops_with_routes = [s for s in BUS_STOPS if s["routes"]]
    print(f"Stops with assigned routes: {len(stops_with_routes)}")
    
    # Check specific examples if possible
    # e.g. "Kempegowda Bus Stand" should have many routes
    majestic = next((s for s in BUS_STOPS if "kempegowda" in s["name"].lower()), None)
    if majestic:
        print(f"Majestic Routes ({len(majestic['routes'])}): {majestic['routes'][:10]}...")
    else:
        print("Majestic stop not found (check naming).")

    # Check "Magadi Road" related
    magadi = [s for s in BUS_STOPS if "magadi road" in s["name"].lower() and s["routes"]]
    if magadi:
        print(f"Found {len(magadi)} Magadi Road stops with routes.")
        print(f"Sample: {magadi[0]['name']} -> {magadi[0]['routes']}")

if __name__ == "__main__":
    test_bus_routes_loading()
