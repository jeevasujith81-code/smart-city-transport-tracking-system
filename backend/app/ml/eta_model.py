import math
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Tuple

try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.preprocessing import StandardScaler
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

class ETAPredictionEngine:
    def __init__(self):
        self.model = None
        self.scaler = None
        self.is_trained = False
        if HAS_SKLEARN:
            self._train_baseline_model()

    def _train_baseline_model(self):
        """Train a baseline Random Forest model on generated historical transit training data."""
        np.random.seed(42)
        n_samples = 1500

        # Features: remaining_dist_km, current_speed_kmh, stop_delta, hour_of_day, day_of_week, avg_route_speed
        remaining_dist = np.random.uniform(0.5, 25.0, n_samples)
        current_speed = np.random.uniform(10.0, 60.0, n_samples)
        stop_delta = np.random.randint(1, 15, n_samples)
        hour = np.random.randint(6, 23, n_samples)
        day_of_week = np.random.randint(0, 7, n_samples)
        avg_route_speed = np.random.uniform(25.0, 45.0, n_samples)

        # Traffic delay factor based on peak hours (7-9 AM, 5-7 PM)
        peak_traffic = np.where((hour >= 7) & (hour <= 9) | (hour >= 17) & (hour <= 19), 1.35, 1.0)
        
        # Base ETA in minutes = (distance / max(speed, 10)) * 60 + stop_dwell_time (1.5 min per stop) * traffic_factor
        base_eta = (remaining_dist / np.maximum(current_speed, 10.0)) * 60.0 + (stop_delta * 1.2)
        actual_eta = base_eta * peak_traffic + np.random.normal(0, 1.5, n_samples)
        actual_eta = np.maximum(actual_eta, 1.0)

        X = np.column_stack([remaining_dist, current_speed, stop_delta, hour, day_of_week, avg_route_speed])
        y = actual_eta

        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        self.model = RandomForestRegressor(n_estimators=50, max_depth=10, random_state=42)
        self.model.fit(X_scaled, y)
        self.is_trained = True

    def predict_eta(
        self, 
        remaining_distance_km: float, 
        current_speed_kmh: float, 
        stop_delta: int = 1,
        average_route_speed: float = 30.0
    ) -> Tuple[float, float]:
        """
        Predicts arrival time in minutes and returns (eta_minutes, confidence_score).
        """
        now = datetime.now()
        hour = now.hour
        day_of_week = now.weekday()

        # Clamp speed to reasonable boundaries
        effective_speed = max(current_speed_kmh, 12.0)
        
        if self.is_trained and HAS_SKLEARN:
            try:
                features = np.array([[
                    remaining_distance_km, 
                    effective_speed, 
                    stop_delta, 
                    hour, 
                    day_of_week, 
                    average_route_speed
                ]])
                scaled_features = self.scaler.transform(features)
                pred_eta = float(self.model.predict(scaled_features)[0])
                
                # Confidence score calculation based on speed variance & model tree variance
                preds = [tree.predict(scaled_features)[0] for tree in self.model.estimators_]
                variance = np.var(preds)
                confidence = float(max(0.70, min(0.98, 1.0 - (variance / 20.0))))
                
                return max(1.0, round(pred_eta, 1)), round(confidence, 2)
            except Exception:
                pass

        # Fallback Heuristic model if sklearn is unavailable or prediction throws
        peak_traffic = 1.3 if (7 <= hour <= 9 or 17 <= hour <= 19) else 1.05
        base_mins = (remaining_distance_km / effective_speed) * 60.0
        dwell_mins = stop_delta * 1.2
        total_eta = (base_mins + dwell_mins) * peak_traffic
        
        confidence = 0.85 if effective_speed > 20 else 0.75
        return max(1.0, round(total_eta, 1)), confidence

# Singleton Instance
eta_engine = ETAPredictionEngine()
