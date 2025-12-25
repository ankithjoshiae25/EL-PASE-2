import xgboost as xgb
import pandas as pd
import heapq
import math
import networkx as nx
from datetime import datetime

class SmartRouter:
    def __init__(self):
        self.model = xgb.XGBRegressor()
        try:
            self.model.load_model("B:\\EL-1st semester\\EL-PASE-2\\traffic_xgb.json")
            print("Loaded XGBoost Traffic Model.")
        except:
            print("Model not found. Please run train_traffic_model.py first.")

        self.locations = {
            "koramangala": [12.9352, 77.6245],
            "whitefield": [12.9698, 77.7500],
            "indiranagar": [12.9784, 77.6408],
            "mg road": [12.9719, 77.6101],
            "electronic city": [12.8452, 77.6602],
            "hsr layout": [12.9121, 77.6446],
            "jayanagar": [12.9308, 77.5838],
            "majestic": [12.9767, 77.5713],
            "hebbal": [13.0334, 77.5891]
        }
        
        self.graph = self._build_graph()

    def _calculate_haversine(self, coord1, coord2):
        R = 6371
        lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
        lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
        a = math.sin((lat2-lat1)/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2-lon1)/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

    def _build_graph(self):
        """
        Creates a NetworkX graph connecting all locations to their nearest neighbors.
        In a real app, this would be a real road network.
        """
        G = nx.Graph()
        keys = list(self.locations.keys())
        
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                loc_a = keys[i]
                loc_b = keys[j]
                dist = self._calculate_haversine(self.locations[loc_a], self.locations[loc_b])
                
                if dist < 8.0:
                    G.add_edge(loc_a, loc_b, distance_km=dist, road_type=1)
                    
        return G

    def predict_edge_weight(self, u, v, current_traffic, current_density):
        """
        Uses XGBoost to predict travel time for a specific edge
        """
        edge_data = self.graph[u][v]
        dist = edge_data['distance_km']
        road_type = edge_data['road_type']
        hour = datetime.now().hour
        
        input_data = pd.DataFrame([{
            'distance_km': dist,
            'traffic_index': current_traffic, 
            'pop_density': current_density,   
            'hour_of_day': hour,
            'road_type': road_type
        }])
        
        predicted_duration = self.model.predict(input_data)[0]
        return max(1.0, predicted_duration) 
    
    def find_optimal_route(self, start_node, end_node, traffic_map, density_map):
        """
        Dijkstra's Algorithm using ML-predicted weights
        """
        if start_node not in self.graph or end_node not in self.graph:
            return None, "Invalid Locations"

        pq = [(0, start_node, [])]
        visited = set()
        min_times = {node: float('inf') for node in self.graph.nodes}
        min_times[start_node] = 0
        
        final_path = []
        final_cost = 0

        while pq:
            current_time, current_node, path = heapq.heappop(pq)
            path = path + [current_node]

            if current_node == end_node:
                final_path = path
                final_cost = current_time
                break

            if current_node in visited:
                continue
            visited.add(current_node)

            for neighbor in self.graph.neighbors(current_node):
                if neighbor not in visited:
                    t_level = traffic_map.get(neighbor, 5.0) 
                    p_density = density_map.get(neighbor, 10000)
                    
                    edge_cost = self.predict_edge_weight(current_node, neighbor, t_level, p_density)
                    
                    new_time = current_time + edge_cost
                    
                    if new_time < min_times[neighbor]:
                        min_times[neighbor] = new_time
                        heapq.heappush(pq, (new_time, neighbor, path))
        
        return {
            "path": final_path,
            "total_duration_mins": round(final_cost, 2),
            "algorithm": "Dijkstra with XGBoost Weights"
        }

if __name__ == "__main__":
    router = SmartRouter()
    
    traffic_conditions = {
        "koramangala": 9.0, 
        "indiranagar": 8.0, 
        "hsr layout": 4.0,
        "majestic": 8.5
    }
    
    pop_density = {
        "koramangala": 25000,
        "hsr layout": 12000
    }
    
    start = "koramangala"
    end = "majestic"
    
    result = router.find_optimal_route(start, end, traffic_conditions, pop_density)
    print(f"Optimal Route from {start} to {end}:")
    print(f"Path: {' -> '.join(result['path'])}")
    print(f"Estimated Time: {result['total_duration_mins']} mins")