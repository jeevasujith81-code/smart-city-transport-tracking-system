import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.api.v1.auth import get_current_user, require_role
from app.models.models import Route, RouteStop, Stop, User, UserRole
from app.schemas.schemas import RouteCreate, RouteResponse, RouteUpdate

router = APIRouter(prefix="/routes", tags=["Routes"])

@router.get("/", response_model=List[RouteResponse])
def get_routes(db: Session = Depends(get_db)):
    return db.query(Route).all()

@router.get("/{route_id}", response_model=RouteResponse)
def get_route(route_id: int, db: Session = Depends(get_db)):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return route

@router.post("/", response_model=RouteResponse, status_code=status.HTTP_201_CREATED)
def create_route(
    route_in: RouteCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    existing = db.query(Route).filter(Route.route_code == route_in.route_code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Route code already exists")

    stop_ids = route_in.stop_ids or []
    route_data = route_in.model_dump(exclude={"stop_ids"})
    
    route = Route(**route_data)
    db.add(route)
    db.commit()
    db.refresh(route)

    # Attach Stops in sequence if provided
    for idx, stop_id in enumerate(stop_ids):
        rs = RouteStop(
            route_id=route.id,
            stop_id=stop_id,
            sequence_order=idx + 1,
            distance_from_start_km=idx * 2.5,
            estimated_time_mins=idx * 5
        )
        db.add(rs)
    
    db.commit()
    db.refresh(route)
    return route

@router.put("/{route_id}", response_model=RouteResponse)
def update_route(
    route_id: int, 
    route_in: RouteUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    update_data = route_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(route, field, value)

    db.commit()
    db.refresh(route)
    return route

@router.delete("/{route_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_route(
    route_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    db.delete(route)
    db.commit()
    return None
