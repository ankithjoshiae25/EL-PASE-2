import pandas as pd
import numpy as np
import xgboost as xgb
import pickle
import random

def generate_traffic_data(n_samples=5000):
    data = []
    
    for _ in range(n_samples):
        distance_km = round(random.uniform(0.5, 15.0), 2)
        traffic_index = round(random.uniform(0, 10), 1) 
        pop_density = round(random.uniform(1000, 30000), 0) 
        hour_of_day = random.randint(0, 23)
        road_type = random.choice([1, 2, 3]) 

        if road_type == 3: base_speed = 60 
        elif road_type == 1: base_speed = 40 
        else: base_speed = 25 
        
        traffic_factor = 1 + (traffic_index / 5.0) 
        density_factor = 1 + (pop_density / 100000.0) 

        duration_mins = (distance_km / base_speed) * 60 * traffic_factor * density_factor
        duration_mins = duration_mins * random.uniform(0.9, 1.1) 
        
        data.append({
            "distance_km": distance_km,
            "traffic_index": traffic_index,
            "pop_density": pop_density,
            "hour_of_day": hour_of_day,
            "road_type": road_type,
            "duration_mins": round(duration_mins, 2)
        })
        
    return pd.DataFrame(data)

# 2. Train XGBoost Model
def train_xgboost():
    print("Generating synthetic traffic data...")
    df = generate_traffic_data()
    
    X = df[['distance_km', 'traffic_index', 'pop_density', 'hour_of_day', 'road_type']]
    y = df['duration_mins']
    
    print("Training XGBoost Regressor...")
    model = xgb.XGBRegressor(
        objective='reg:squarederror',
        n_estimators=100,
        learning_rate=0.1,
        max_depth=5
    )
    model.fit(X, y)
    
    score = model.score(X, y)
    print(f"Model R2 Score: {score:.4f}")
    
    model.save_model("traffic_xgb.json")
    print("Model saved to traffic_xgb.json")

if __name__ == "__main__":
    train_xgboost()