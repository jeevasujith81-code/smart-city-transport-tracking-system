from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
from app.models.models import UserRole, BusStatus, TripStatus, AlertSeverity, FavoriteType, CrowdLevel

# Auth & User
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: Optional[UserRole] = UserRole.PASSENGER

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: int
    full_name: str
    email: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Driver
class DriverBase(BaseModel):
    license_number: str
    phone: Optional[str] = None
    status: Optional[str] = "AVAILABLE"
    assigned_bus_id: Optional[int] = None

class DriverCreate(DriverBase):
    user_id: int

class DriverUpdate(BaseModel):
    license_number: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[str] = None
    assigned_bus_id: Optional[int] = None

class DriverResponse(DriverBase):
    id: int
    user_id: int
    user: Optional[UserResponse] = None

    class Config:
        from_attributes = True

# Stop
class StopBase(BaseModel):
    stop_name: str
    code: str
    latitude: float
    longitude: float
    city_area: Optional[str] = "Downtown"

class StopCreate(StopBase):
    pass

class StopUpdate(BaseModel):
    stop_name: Optional[str] = None
    code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    city_area: Optional[str] = None

class StopResponse(StopBase):
    id: int

    class Config:
        from_attributes = True

# Route Stop
class RouteStopBase(BaseModel):
    stop_id: int
    sequence_order: int
    distance_from_start_km: float = 0.0
    estimated_time_mins: int = 0

class RouteStopResponse(RouteStopBase):
    id: int
    stop: StopResponse

    class Config:
        from_attributes = True

# Route
class RouteBase(BaseModel):
    route_name: str
    route_code: str
    origin: str
    destination: str
    total_distance_km: float = 0.0
    polyline_coords: Optional[str] = None

class RouteCreate(RouteBase):
    stop_ids: Optional[List[int]] = []

class RouteUpdate(BaseModel):
    route_name: Optional[str] = None
    route_code: Optional[str] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    total_distance_km: Optional[float] = None
    polyline_coords: Optional[str] = None

class RouteResponse(RouteBase):
    id: int
    route_stops: List[RouteStopResponse] = []

    class Config:
        from_attributes = True

# Bus
class BusBase(BaseModel):
    bus_number: str
    capacity: int = 40
    model: str = "City Transit 3000"
    status: BusStatus = BusStatus.ACTIVE
    crowd_level: CrowdLevel = CrowdLevel.LOW
    assigned_route_id: Optional[int] = None
    assigned_driver_id: Optional[int] = None

class BusCreate(BusBase):
    pass

class BusUpdate(BaseModel):
    bus_number: Optional[str] = None
    capacity: Optional[int] = None
    model: Optional[str] = None
    status: Optional[BusStatus] = None
    crowd_level: Optional[CrowdLevel] = None
    assigned_route_id: Optional[int] = None
    assigned_driver_id: Optional[int] = None

class BusResponse(BusBase):
    id: int
    route: Optional[RouteResponse] = None

    class Config:
        from_attributes = True

# Bus Location
class BusLocationCreate(BaseModel):
    bus_id: int
    trip_id: Optional[int] = None
    latitude: float
    longitude: float
    speed_kmh: float = 0.0
    crowd_level: Optional[CrowdLevel] = CrowdLevel.LOW
    current_stop_id: Optional[int] = None
    next_stop_id: Optional[int] = None

class BusLocationResponse(BusLocationCreate):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True

# Trip
class TripBase(BaseModel):
    bus_id: int
    driver_id: int
    route_id: int
    status: TripStatus = TripStatus.SCHEDULED

class TripCreate(TripBase):
    pass

class TripUpdate(BaseModel):
    status: Optional[TripStatus] = None
    end_time: Optional[datetime] = None

class TripResponse(TripBase):
    id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    bus: Optional[BusResponse] = None
    driver: Optional[DriverResponse] = None
    route: Optional[RouteResponse] = None
    latest_location: Optional[BusLocationResponse] = None

    class Config:
        from_attributes = True

# ETA
class ETAResponse(BaseModel):
    bus_id: int
    bus_number: str
    stop_id: int
    stop_name: str
    predicted_eta_minutes: float
    confidence_score: float
    current_speed_kmh: float
    remaining_distance_km: float
    formatted_eta: str
    status: str

# Alert
class AlertBase(BaseModel):
    title: str
    description: str
    severity: AlertSeverity = AlertSeverity.INFO
    route_id: Optional[int] = None
    expires_at: Optional[datetime] = None

class AlertCreate(AlertBase):
    pass

class AlertUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[AlertSeverity] = None
    route_id: Optional[int] = None
    expires_at: Optional[datetime] = None

class AlertResponse(AlertBase):
    id: int
    created_at: datetime
    route: Optional[RouteResponse] = None

    class Config:
        from_attributes = True

# Favorite
class FavoriteCreate(BaseModel):
    target_type: FavoriteType
    target_id: int

class FavoriteResponse(BaseModel):
    id: int
    user_id: int
    target_type: FavoriteType
    target_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Analytics
class AnalyticsSummary(BaseModel):
    total_buses: int
    active_buses: int
    offline_buses: int
    total_routes: int
    total_stops: int
    total_drivers: int
    total_passengers: int
    active_trips: int
    average_delay_mins: float
    daily_trips_chart: List[dict]
    route_popularity: List[dict]
    peak_hours_chart: List[dict]
