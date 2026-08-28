import math
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.api.v1.auth import get_current_user, require_role
from app.models.models import Stop, User, UserRole
from app.schemas.schemas import StopCreate, StopResponse, StopUpdate
from app.services.eta_service import haversine_distance_km

router = APIRouter(prefix="/stops", tags=["Stops"])

@router.get("/", response_model=List[StopResponse])
def get_stops(db: Session = Depends(get_db)):
    return db.query(Stop).all()

@router.get("/nearby", response_model=List[dict])
def get_nearby_stops(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    radius_km: float = Query(5.0, description="Radius in km"),
    db: Session = Depends(get_db)
):
    stops = db.query(Stop).all()
    nearby_list = []
    
    for s in stops:
        dist = haversine_distance_km(lat, lng, s.latitude, s.longitude)
        if dist <= radius_km:
            stop_dict = StopResponse.model_validate(s).model_dump()
            stop_dict["distance_km"] = round(dist, 2)
            nearby_list.append(stop_dict)
            
    nearby_list.sort(key=lambda x: x["distance_km"])
    return nearby_list

@router.get("/{stop_id}", response_model=StopResponse)
def get_stop(stop_id: int, db: Session = Depends(get_db)):
    stop = db.query(Stop).filter(Stop.id == stop_id).first()
    if not stop:
        raise HTTPException(status_code=404, detail="Stop not found")
    return stop

@router.get("/{stop_id}/eta")
def get_stop_incoming_etas(stop_id: int, db: Session = Depends(get_db)):
    from app.models.models import Bus
    from app.services.eta_service import calculate_bus_eta

    stop = db.query(Stop).filter(Stop.id == stop_id).first()
    if not stop:
        raise HTTPException(status_code=404, detail="Stop not found")

    buses = db.query(Bus).all()
    eta_results = []
    for b in buses:
        try:
            res = calculate_bus_eta(db=db, bus_id=b.id, stop_id=stop_id)
            eta_results.append(res)
        except Exception:
            pass

    eta_results.sort(key=lambda x: x["predicted_eta_minutes"])
    return eta_results

@router.post("/", response_model=StopResponse, status_code=status.HTTP_201_CREATED)
def create_stop(
    stop_in: StopCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    existing = db.query(Stop).filter(Stop.code == stop_in.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Stop code already exists")

    stop = Stop(**stop_in.model_dump())
    db.add(stop)
    db.commit()
    db.refresh(stop)
    return stop

@router.put("/{stop_id}", response_model=StopResponse)
def update_stop(
    stop_id: int, 
    stop_in: StopUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    stop = db.query(Stop).filter(Stop.id == stop_id).first()
    if not stop:
        raise HTTPException(status_code=404, detail="Stop not found")

    update_data = stop_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(stop, field, value)

    db.commit()
    db.refresh(stop)
    return stop

@router.delete("/{stop_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_stop(
    stop_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    stop = db.query(Stop).filter(Stop.id == stop_id).first()
    if not stop:
        raise HTTPException(status_code=404, detail="Stop not found")
    db.delete(stop)
    db.commit()
    return None
