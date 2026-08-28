from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.api.v1.auth import get_current_user, require_role
from app.models.models import Driver, Bus, User, UserRole
from app.schemas.schemas import DriverCreate, DriverResponse, DriverUpdate

router = APIRouter(prefix="/drivers", tags=["Drivers"])

@router.get("/", response_model=List[DriverResponse])
def get_drivers(db: Session = Depends(get_db)):
    return db.query(Driver).all()

@router.get("/me", response_model=DriverResponse)
def get_driver_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.DRIVER, UserRole.ADMIN]))
):
    driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")
    return driver

@router.get("/{driver_id}", response_model=DriverResponse)
def get_driver(driver_id: int, db: Session = Depends(get_db)):
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    return driver

@router.post("/", response_model=DriverResponse, status_code=status.HTTP_201_CREATED)
def create_driver(
    driver_in: DriverCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    existing = db.query(Driver).filter(Driver.user_id == driver_in.user_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="User is already registered as a driver")

    driver = Driver(**driver_in.model_dump())
    db.add(driver)
    db.commit()
    db.refresh(driver)
    return driver

@router.put("/{driver_id}", response_model=DriverResponse)
def update_driver(
    driver_id: int, 
    driver_in: DriverUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.DRIVER]))
):
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    update_data = driver_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(driver, field, value)

    # Sync Bus driver assignment if assigned_bus_id changed
    if "assigned_bus_id" in update_data and update_data["assigned_bus_id"]:
        bus = db.query(Bus).filter(Bus.id == update_data["assigned_bus_id"]).first()
        if bus:
            bus.assigned_driver_id = driver.id

    db.commit()
    db.refresh(driver)
    return driver
