import time
import math
import requests
import json
import logging
from typing import List, Dict

logging.basicConfig(level=logging.INFO, format="%(asctime)s - GPS_SIMULATOR - %(levelname)s - %(message)s")
logger = logging.getLogger("gps_simulator")

API_BASE_URL = "http://localhost:8000/api/v1"

class GPSBusSimulator:
    def __init__(self, api_url: str = API_BASE_URL, simulation_speed: float = 1.0):
        self.api_url = api_url
        self.simulation_speed = simulation_speed
        self.is_running = False
        self.active_trips: List[Dict] = []

    def fetch_active_trips(self):
        try:
            res = requests.get(f"{self.api_url}/trips/active", timeout=5)
            if res.status_code == 200:
                self.active_trips = res.json()
                logger.info(f"Loaded {len(self.active_trips)} active trips for GPS simulation.")
            else:
                logger.warning(f"Failed to fetch active trips. Status: {res.status_code}")
        except Exception as e:
            logger.error(f"Error fetching active trips: {e}")

    def interpolate_points(self, p1: List[float], p2: List[float], num_steps: int = 10) -> List[List[float]]:
        """Interpolates between two coordinates [lat, lng]."""
        lats = [p1[0] + (p2[0] - p1[0]) * (i / num_steps) for i in range(num_steps + 1)]
        lngs = [p1[1] + (p2[1] - p1[1]) * (i / num_steps) for i in range(num_steps + 1)]
        return list(zip(lats, lngs))

    def run_simulation_loop(self, max_iterations: int = 100):
        self.fetch_active_trips()
        if not self.active_trips:
            logger.warning("No active trips found. Creating a simulation fallback...")
            return

        self.is_running = True
        step = 0
        logger.info(f"Starting GPS simulation loop (Speed multiplier: {self.simulation_speed}x)...")

        while self.is_running and step < max_iterations:
            step += 1
            for trip in self.active_trips:
                trip_id = trip["id"]
                bus_id = trip["bus_id"]
                route = trip.get("route")
                
                if not route or not route.get("polyline_coords"):
                    continue

                try:
                    coords = json.loads(route["polyline_coords"])
                except Exception:
                    continue

                if len(coords) < 2:
                    continue

                # Progress along route polylines based on current step
                coord_idx = (step) % (len(coords) - 1)
                p1 = coords[coord_idx]
                p2 = coords[coord_idx + 1]

                # Current interpolated lat/lng
                sub_step = (step % 5) / 5.0
                curr_lat = p1[0] + (p2[0] - p1[0]) * sub_step
                curr_lng = p1[1] + (p2[1] - p1[1]) * sub_step

                speed = 25.0 + ((step % 7) * 3.5)
                crowd_levels = ["LOW", "MEDIUM", "HIGH", "FULL"]
                crowd_val = crowd_levels[(bus_id + step // 10) % len(crowd_levels)]

                payload = {
                    "bus_id": bus_id,
                    "trip_id": trip_id,
                    "latitude": round(curr_lat, 6),
                    "longitude": round(curr_lng, 6),
                    "speed_kmh": round(speed, 1),
                    "crowd_level": crowd_val
                }

                try:
                    loc_res = requests.post(
                        f"{self.api_url}/trips/{trip_id}/location",
                        json=payload,
                        timeout=3
                    )
                    if loc_res.status_code == 200:
                        logger.info(f"Bus {bus_id} location updated: Lat {curr_lat:.5f}, Lng {curr_lng:.5f}, Speed {speed:.1f} km/h")
                except Exception as e:
                    logger.error(f"Error posting GPS update for Bus {bus_id}: {e}")

            time.sleep(max(0.5, 3.0 / self.simulation_speed))

    def stop(self):
        self.is_running = False
        logger.info("GPS simulation stopped.")

if __name__ == "__main__":
    simulator = GPSBusSimulator(simulation_speed=2.0)
    try:
        simulator.run_simulation_loop(max_iterations=50)
    except KeyboardInterrupt:
        simulator.stop()
