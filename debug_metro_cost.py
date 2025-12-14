
import csv
import os

METRO_FARES = []

def load_fares():
    global METRO_FARES
    try:
        fares_path = "namma_metro_fares.csv"
        print(f"Loading fares from {os.path.abspath(fares_path)}")
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
                except ValueError as e:
                    print(f"Error parsing row {row}: {e}")
                    continue
            
        # Ensure fares are sorted by distance range
        METRO_FARES.sort(key=lambda x: x[0])
        print(f"Loaded {len(METRO_FARES)} fare ranges.")
        for f in METRO_FARES:
            print(f"Max Dist: {f[0]}, Fare: {f[1]}")
            
    except Exception as e:
        print(f"Error loading fare data: {e}")

def get_metro_fare(distance_km):
    """Calculate metro fare based on distance"""
    for max_dist, fare in METRO_FARES:
        if distance_km <= max_dist:
            return fare
    # Default fallback if distance exceeds all ranges (though 'inf' handles this)
    return 90.0

if __name__ == "__main__":
    load_fares()
    
    test_distances = [1.5, 3.0, 5.0, 7.0, 12.0, 18.0, 22.0, 28.0, 35.0]
    print("\nTesting Fares:")
    for d in test_distances:
        print(f"Distance: {d} km -> Fare: {get_metro_fare(d)}")
