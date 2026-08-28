from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.api.v1.auth import get_current_user, require_role
from app.models.models import Bus, User, UserRole, BusLocation
from app.schemas.schemas import BusCreate, BusResponse, BusUpdate, BusLocationResponse

router = APIRouter(prefix="/buses", tags=["Buses"])

@router.get("/", response_model=List[BusResponse])
def get_buses(db: Session = Depends(get_db)):
    return db.query(Bus).all()

@router.get("/{bus_id}", response_model=BusResponse)
def get_bus(bus_id: int, db: Session = Depends(get_db)):
    bus = db.query(Bus).filter(Bus.id == bus_id).first()
    if not bus:
        raise HTTPException(status_code=404, detail="Bus not found")
    return bus

@router.get("/locations/active")
def get_active_bus_locations(db: Session = Depends(get_db)):
    buses = db.query(Bus).all()
    active_locs = []
    for b in buses:
        latest = (
            db.query(BusLocation)
            .filter(BusLocation.bus_id == b.id)
            .order_by(BusLocation.timestamp.desc())
            .first()
        )
        if latest:
            crowd_str = b.crowd_level.value if hasattr(b.crowd_level, "value") else (b.crowd_level or "LOW")
            active_locs.append({
                "bus_id": b.id,
                "bus_number": b.bus_number,
                "latitude": latest.latitude,
                "longitude": latest.longitude,
                "speed_kmh": latest.speed_kmh,
                "crowd_level": crowd_str,
                "timestamp": latest.timestamp.isoformat()
            })
    return active_locs

@router.get("/{bus_id}/location", response_model=Optional[BusLocationResponse])
def get_bus_location(bus_id: int, db: Session = Depends(get_db)):
    latest_location = (
        db.query(BusLocation)
        .filter(BusLocation.bus_id == bus_id)
        .order_by(BusLocation.timestamp.desc())
        .first()
    )
    return latest_location

@router.post("/", response_model=BusResponse, status_code=status.HTTP_201_CREATED)
def create_bus(
    bus_in: BusCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    existing = db.query(Bus).filter(Bus.bus_number == bus_in.bus_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Bus number already exists")

    bus = Bus(**bus_in.model_dump())
    db.add(bus)
    db.commit()
    db.refresh(bus)
    return bus

@router.put("/{bus_id}", response_model=BusResponse)
def update_bus(
    bus_id: int, 
    bus_in: BusUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    bus = db.query(Bus).filter(Bus.id == bus_id).first()
    if not bus:
        raise HTTPException(status_code=404, detail="Bus not found")

    update_data = bus_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(bus, field, value)

    db.commit()
    db.refresh(bus)
    return bus

@router.delete("/{bus_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bus(
    bus_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    bus = db.query(Bus).filter(Bus.id == bus_id).first()
    if not bus:
        raise HTTPException(status_code=404, detail="Bus not found")
    db.delete(bus)
    db.commit()
    return None
