import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.models import Route, Stop, RouteStop, Bus, BusLocation, Trip, TripStatus

router = APIRouter(prefix="/planner", tags=["Route Planner"])

@router.get("/route")
def plan_transit_route(
    origin_stop_id: int = Query(..., description="ID of the starting bus stop"),
    destination_stop_id: int = Query(..., description="ID of the destination bus stop"),
    db: Session = Depends(get_db)
):
    if origin_stop_id == destination_stop_id:
        raise HTTPException(status_code=400, detail="Origin and destination stops cannot be identical.")

    origin_stop = db.query(Stop).filter(Stop.id == origin_stop_id).first()
    dest_stop = db.query(Stop).filter(Stop.id == destination_stop_id).first()

    if not origin_stop:
        raise HTTPException(status_code=404, detail="Origin stop not found")
    if not dest_stop:
        raise HTTPException(status_code=404, detail="Destination stop not found")

    # Find candidate routes containing origin stop
    origin_route_stops = db.query(RouteStop).filter(RouteStop.stop_id == origin_stop_id).all()
    
    route_options = []

    for ors in origin_route_stops:
        # Check if destination stop exists on the same route and comes after origin
        drs = (
            db.query(RouteStop)
            .filter(
                RouteStop.route_id == ors.route_id,
                RouteStop.stop_id == destination_stop_id,
                RouteStop.sequence_order > ors.sequence_order
            )
            .first()
        )

        if drs:
            route = db.query(Route).filter(Route.id == ors.route_id).first()
            if not route:
                continue

            # Calculate intermediate stops and distance
            intermediate_stops_count = drs.sequence_order - ors.sequence_order
            distance_km = round(drs.distance_from_start_km - ors.distance_from_start_km, 2)
            if distance_km <= 0:
                distance_km = round(route.total_distance_km or 5.0, 1)

            est_time_mins = drs.estimated_time_mins - ors.estimated_time_mins
            if est_time_mins <= 0:
                est_time_mins = max(5, int(distance_km * 2.5))

            # Fetch active buses running on this route
            active_buses_data = []
            buses_on_route = db.query(Bus).filter(Bus.assigned_route_id == route.id).all()
            for b in buses_on_route:
                latest_loc = (
                    db.query(BusLocation)
                    .filter(BusLocation.bus_id == b.id)
                    .order_by(BusLocation.timestamp.desc())
                    .first()
                )
                crowd_str = b.crowd_level.value if hasattr(b.crowd_level, "value") else (b.crowd_level or "LOW")
                active_buses_data.append({
                    "bus_id": b.id,
                    "bus_number": b.bus_number,
                    "capacity": b.capacity,
                    "model": b.model,
                    "status": b.status.value if hasattr(b.status, "value") else b.status,
                    "crowd_level": crowd_str,
                    "location": {
                        "latitude": latest_loc.latitude,
                        "longitude": latest_loc.longitude,
                        "speed_kmh": latest_loc.speed_kmh,
                        "timestamp": latest_loc.timestamp.isoformat()
                    } if latest_loc else None
                })

            # Parse polyline if present
            polyline_list = []
            if route.polyline_coords:
                try:
                    polyline_list = json.loads(route.polyline_coords)
                except Exception:
                    polyline_list = []

            route_options.append({
                "route_id": route.id,
                "route_code": route.route_code,
                "route_name": route.route_name,
                "origin_stop_sequence": ors.sequence_order,
                "dest_stop_sequence": drs.sequence_order,
                "stops_count": intermediate_stops_count,
                "distance_km": max(0.5, distance_km),
                "estimated_travel_time_mins": est_time_mins,
                "active_buses": active_buses_data,
                "polyline_coords": polyline_list
            })

    return {
        "origin_stop": {
            "id": origin_stop.id,
            "name": origin_stop.stop_name,
            "code": origin_stop.code,
            "latitude": origin_stop.latitude,
            "longitude": origin_stop.longitude,
            "city_area": origin_stop.city_area
        },
        "destination_stop": {
            "id": dest_stop.id,
            "name": dest_stop.stop_name,
            "code": dest_stop.code,
            "latitude": dest_stop.latitude,
            "longitude": dest_stop.longitude,
            "city_area": dest_stop.city_area
        },
        "total_routes_found": len(route_options),
        "options": route_options
    }
