import pandas as pd
from sklearn.linear_model import LinearRegression
import sys

def train_models():
    try:
        df = pd.read_csv('mock_ride_fare_dataset.csv')
        
        platforms = df['platform'].unique()
        results = {}
        
        print("Training models for platforms:", platforms)
        
        for platform in platforms:
            subset = df[df['platform'] == platform]
            X = subset[['distance_km', 'time_minutes']]
            y = subset['total_fare']
            
            model = LinearRegression()
            model.fit(X, y)
            
            results[platform] = {
                'intercept': model.intercept_,
                'coef_dist': model.coef_[0],
                'coef_time': model.coef_[1],
                'r2': model.score(X, y)
            }
            
            print(f"\nPlatform: {platform}")
            print(f"  Intercept (Base Fare approx): {model.intercept_:.2f}")
            print(f"  Coefficient Distance (per km): {model.coef_[0]:.2f}")
            print(f"  Coefficient Time (per min): {model.coef_[1]:.2f}")
            print(f"  R2 Score: {model.score(X, y):.4f}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    train_models()
