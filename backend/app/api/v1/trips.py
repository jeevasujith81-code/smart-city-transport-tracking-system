from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.api.v1.auth import get_current_user, require_role
from app.models.models import Trip, TripStatus, Bus, Driver, BusLocation, User, UserRole
from app.schemas.schemas import TripCreate, TripResponse, TripUpdate, BusLocationCreate, BusLocationResponse
from app.services.websocket_manager import manager

router = APIRouter(prefix="/trips", tags=["Trips"])

@router.get("/", response_model=List[TripResponse])
def get_trips(db: Session = Depends(get_db)):
    trips = db.query(Trip).all()
    for trip in trips:
        trip.latest_location = (
            db.query(BusLocation)
            .filter(BusLocation.bus_id == trip.bus_id)
            .order_by(BusLocation.timestamp.desc())
            .first()
        )
    return trips

@router.get("/active", response_model=List[TripResponse])
def get_active_trips(db: Session = Depends(get_db)):
    trips = db.query(Trip).filter(Trip.status == TripStatus.IN_PROGRESS).all()
    for trip in trips:
        trip.latest_location = (
            db.query(BusLocation)
            .filter(BusLocation.bus_id == trip.bus_id)
            .order_by(BusLocation.timestamp.desc())
            .first()
        )
    return trips

@router.get("/{trip_id}", response_model=TripResponse)
def get_trip(trip_id: int, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    trip.latest_location = (
        db.query(BusLocation)
        .filter(BusLocation.bus_id == trip.bus_id)
        .order_by(BusLocation.timestamp.desc())
        .first()
    )
    return trip

@router.post("/", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
def create_trip(
    trip_in: TripCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.DRIVER]))
):
    trip = Trip(
        bus_id=trip_in.bus_id,
        driver_id=trip_in.driver_id,
        route_id=trip_in.route_id,
        status=TripStatus.IN_PROGRESS,
        start_time=datetime.utcnow()
    )
    db.add(trip)
    
    # Update driver status
    driver = db.query(Driver).filter(Driver.id == trip_in.driver_id).first()
    if driver:
        driver.status = "ON_TRIP"
        
    db.commit()
    db.refresh(trip)
    return trip

@router.put("/{trip_id}/status", response_model=TripResponse)
def update_trip_status(
    trip_id: int,
    status_update: TripUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.DRIVER]))
):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    if status_update.status:
        trip.status = status_update.status
        if status_update.status in [TripStatus.COMPLETED, TripStatus.CANCELLED]:
            trip.end_time = datetime.utcnow()
            driver = db.query(Driver).filter(Driver.id == trip.driver_id).first()
            if driver:
                driver.status = "AVAILABLE"

    db.commit()
    db.refresh(trip)
    return trip

@router.post("/{trip_id}/location", response_model=BusLocationResponse)
async def update_trip_location(
    trip_id: int,
    loc_in: BusLocationCreate,
    db: Session = Depends(get_db)
):
    bus = db.query(Bus).filter(Bus.id == loc_in.bus_id).first()
    crowd_val = loc_in.crowd_level.value if hasattr(loc_in.crowd_level, 'value') else loc_in.crowd_level
    if not crowd_val:
        crowd_val = bus.crowd_level.value if (bus and hasattr(bus.crowd_level, 'value')) else "LOW"

    loc_record = BusLocation(
        bus_id=loc_in.bus_id,
        trip_id=trip_id,
        latitude=loc_in.latitude,
        longitude=loc_in.longitude,
        speed_kmh=loc_in.speed_kmh,
        crowd_level=crowd_val,
        current_stop_id=loc_in.current_stop_id,
        next_stop_id=loc_in.next_stop_id,
        timestamp=datetime.utcnow()
    )
    db.add(loc_record)

    if bus and loc_in.crowd_level:
        bus.crowd_level = loc_in.crowd_level

    db.commit()
    db.refresh(loc_record)

    # Broadcast via WebSocket manager to all connected passengers and dashboards
    bus_number = bus.bus_number if bus else f"BUS-{loc_in.bus_id}"
    route_name = bus.route.route_name if (bus and bus.route) else "City Route"

    broadcast_payload = {
        "type": "BUS_LOCATION_UPDATE",
        "data": {
            "bus_id": loc_in.bus_id,
            "bus_number": bus_number,
            "route_name": route_name,
            "trip_id": trip_id,
            "latitude": loc_in.latitude,
            "longitude": loc_in.longitude,
            "speed_kmh": loc_in.speed_kmh,
            "crowd_level": crowd_val,
            "current_stop_id": loc_in.current_stop_id,
            "next_stop_id": loc_in.next_stop_id,
            "timestamp": loc_record.timestamp.isoformat()
        }
    }
    await manager.broadcast(broadcast_payload)

    return loc_record
