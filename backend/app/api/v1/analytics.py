from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.api.v1.auth import get_current_user, require_role
from app.models.models import Bus, BusStatus, Route, Stop, Driver, User, UserRole, Trip, TripStatus
from app.schemas.schemas import AnalyticsSummary

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/summary", response_model=AnalyticsSummary)
def get_analytics_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    total_buses = db.query(Bus).count()
    active_buses = db.query(Bus).filter(Bus.status == BusStatus.ACTIVE).count()
    offline_buses = db.query(Bus).filter(Bus.status != BusStatus.ACTIVE).count()
    total_routes = db.query(Route).count()
    total_stops = db.query(Stop).count()
    total_drivers = db.query(Driver).count()
    total_passengers = db.query(User).filter(User.role == UserRole.PASSENGER).count()
    active_trips = db.query(Trip).filter(Trip.status == TripStatus.IN_PROGRESS).count()

    daily_trips_chart = [
        {"day": "Mon", "trips": 120, "on_time_rate": 94},
        {"day": "Tue", "trips": 135, "on_time_rate": 92},
        {"day": "Wed", "trips": 142, "on_time_rate": 96},
        {"day": "Thu", "trips": 138, "on_time_rate": 91},
        {"day": "Fri", "trips": 150, "on_time_rate": 89},
        {"day": "Sat", "trips": 110, "on_time_rate": 97},
        {"day": "Sun", "trips": 95, "on_time_rate": 98},
    ]

    route_popularity = [
        {"route": "Route 101 - Central Express", "passengers": 3450, "trips": 42},
        {"route": "Route 202 - City Loop", "passengers": 2890, "trips": 38},
        {"route": "Route 303 - Tech Park Shuttle", "passengers": 4120, "trips": 50},
        {"route": "Route 404 - Airport Link", "passengers": 1950, "trips": 24},
        {"route": "Route 505 - North Suburban", "passengers": 2300, "trips": 30},
    ]

    peak_hours_chart = [
        {"hour": "06:00", "ridership": 220},
        {"hour": "08:00", "ridership": 890},
        {"hour": "10:00", "ridership": 450},
        {"hour": "12:00", "ridership": 510},
        {"hour": "14:00", "ridership": 480},
        {"hour": "17:00", "ridership": 940},
        {"hour": "19:00", "ridership": 620},
        {"hour": "21:00", "ridership": 280},
    ]

    return AnalyticsSummary(
        total_buses=total_buses,
        active_buses=active_buses,
        offline_buses=offline_buses,
        total_routes=total_routes,
        total_stops=total_stops,
        total_drivers=total_drivers,
        total_passengers=total_passengers,
        active_trips=active_trips,
        average_delay_mins=2.4,
        daily_trips_chart=daily_trips_chart,
        route_popularity=route_popularity,
        peak_hours_chart=peak_hours_chart
    )
