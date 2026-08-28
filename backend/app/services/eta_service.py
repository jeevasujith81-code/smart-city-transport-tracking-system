import math
import json
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.models import Bus, Stop, Route, RouteStop, BusLocation, ETAPrediction
from app.ml.eta_model import eta_engine

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate geodesic distance between two points in km."""
    R = 6371.0 # Radius of the earth in km
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    rLat1 = math.radians(lat1)
    rLat2 = math.radians(lat2)

    a = math.sin(dLat/2)**2 + math.cos(rLat1) * math.cos(rLat2) * math.sin(dLon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def calculate_bus_eta(db: Session, bus_id: int, stop_id: int):
    # 1. Fetch Bus & Latest Location
    bus = db.query(Bus).filter(Bus.id == bus_id).first()
    if not bus:
        raise HTTPException(status_code=404, detail="Bus not found")
    
    stop = db.query(Stop).filter(Stop.id == stop_id).first()
    if not stop:
        raise HTTPException(status_code=404, detail="Target stop not found")

    latest_loc = db.query(BusLocation).filter(BusLocation.bus_id == bus_id).order_by(BusLocation.timestamp.desc()).first()
    
    # Default coordinates if no location recorded yet
    bus_lat = latest_loc.latitude if latest_loc else 12.9716
    bus_lng = latest_loc.longitude if latest_loc else 77.5946
    speed_kmh = latest_loc.speed_kmh if (latest_loc and latest_loc.speed_kmh > 5) else 30.0

    # 2. Check route progress & stop sequence
    stop_delta = 1
    if bus.assigned_route_id:
        route_stops = db.query(RouteStop).filter(RouteStop.route_id == bus.assigned_route_id).order_by(RouteStop.sequence_order).all()
        target_rs = next((rs for rs in route_stops if rs.stop_id == stop_id), None)
        if target_rs:
            # Estimate sequence delta
            stop_delta = max(1, target_rs.sequence_order)

    # 3. Calculate distance
    remaining_dist_km = haversine_distance_km(bus_lat, bus_lng, stop.latitude, stop.longitude)

    # 4. ML Engine Prediction
    eta_mins, confidence = eta_engine.predict_eta(
        remaining_distance_km=remaining_dist_km,
        current_speed_kmh=speed_kmh,
        stop_delta=stop_delta,
        average_route_speed=32.0
    )

    # Format human-readable ETA
    if eta_mins <= 1.0:
        formatted = "Arriving now"
        status_text = "At / Approaching Stop"
    else:
        formatted = f"{int(round(eta_mins))} mins"
        status_text = "On time" if confidence > 0.8 else "Slight delay possible"

    # 5. Save ETA prediction log in DB
    try:
        prediction_record = ETAPrediction(
            bus_id=bus_id,
            stop_id=stop_id,
            predicted_eta_minutes=eta_mins,
            confidence_score=confidence,
            model_version="rf_v1.0"
        )
        db.add(prediction_record)
        db.commit()
    except Exception:
        db.rollback()

    crowd_val = bus.crowd_level.value if hasattr(bus.crowd_level, "value") else (bus.crowd_level or "LOW")

    return {
        "bus_id": bus.id,
        "bus_number": bus.bus_number,
        "stop_id": stop.id,
        "stop_name": stop.stop_name,
        "predicted_eta_minutes": eta_mins,
        "confidence_score": confidence,
        "current_speed_kmh": round(speed_kmh, 1),
        "remaining_distance_km": round(remaining_dist_km, 2),
        "formatted_eta": formatted,
        "status": status_text,
        "crowd_level": crowd_val
    }
