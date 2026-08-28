from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.schemas import ETAResponse
from app.services.eta_service import calculate_bus_eta

router = APIRouter(prefix="/eta", tags=["ETA Prediction"])

@router.get("/{bus_id}/{stop_id}", response_model=ETAResponse)
def get_bus_eta(bus_id: int, stop_id: int, db: Session = Depends(get_db)):
    """
    Predict real-time ETA for a bus arriving at a specific stop.
    Uses Scikit-learn Random Forest model trained on historical speed, distance, and time of day data.
    """
    eta_data = calculate_bus_eta(db=db, bus_id=bus_id, stop_id=stop_id)
    return eta_data
