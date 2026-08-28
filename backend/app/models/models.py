import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum as SQLEnum, Text, Index
)
from sqlalchemy.orm import relationship

from app.core.db import Base

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    DRIVER = "DRIVER"
    PASSENGER = "PASSENGER"

class BusStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    MAINTENANCE = "MAINTENANCE"

class TripStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class AlertSeverity(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

class FavoriteType(str, enum.Enum):
    BUS = "BUS"
    ROUTE = "ROUTE"
    STOP = "STOP"

class CrowdLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    FULL = "FULL"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.PASSENGER, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    driver_profile = relationship("Driver", back_populates="user", uselist=False)
    favorites = relationship("Favorite", back_populates="user", cascade="all, delete-orphan")

class Driver(Base):
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    license_number = Column(String, unique=True, nullable=False)
    phone = Column(String, nullable=True)
    status = Column(String, default="AVAILABLE") # AVAILABLE, ON_TRIP, OFF_DUTY
    assigned_bus_id = Column(Integer, ForeignKey("buses.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    user = relationship("User", back_populates="driver_profile")
    bus = relationship("Bus", foreign_keys=[assigned_bus_id])
    trips = relationship("Trip", back_populates="driver")

class Bus(Base):
    __tablename__ = "buses"

    id = Column(Integer, primary_key=True, index=True)
    bus_number = Column(String, unique=True, index=True, nullable=False)
    capacity = Column(Integer, default=40)
    model = Column(String, default="City Transit 3000")
    status = Column(SQLEnum(BusStatus), default=BusStatus.ACTIVE, nullable=False)
    crowd_level = Column(SQLEnum(CrowdLevel), default=CrowdLevel.LOW, nullable=False)
    assigned_route_id = Column(Integer, ForeignKey("routes.id", ondelete="SET NULL"), nullable=True)
    assigned_driver_id = Column(Integer, ForeignKey("drivers.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    route = relationship("Route", back_populates="buses")
    assigned_driver = relationship("Driver", foreign_keys=[assigned_driver_id])
    trips = relationship("Trip", back_populates="bus")
    locations = relationship("BusLocation", back_populates="bus", cascade="all, delete-orphan")
    eta_predictions = relationship("ETAPrediction", back_populates="bus", cascade="all, delete-orphan")


class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    route_name = Column(String, nullable=False)
    route_code = Column(String, unique=True, index=True, nullable=False)
    origin = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    total_distance_km = Column(Float, default=0.0)
    polyline_coords = Column(Text, nullable=True) # JSON list of [lat, lng]

    # Relationships
    buses = relationship("Bus", back_populates="route")
    route_stops = relationship("RouteStop", back_populates="route", cascade="all, delete-orphan", order_by="RouteStop.sequence_order")
    trips = relationship("Trip", back_populates="route")
    alerts = relationship("Alert", back_populates="route")

class Stop(Base):
    __tablename__ = "stops"

    id = Column(Integer, primary_key=True, index=True)
    stop_name = Column(String, index=True, nullable=False)
    code = Column(String, unique=True, index=True, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    city_area = Column(String, default="Downtown")

    # Relationships
    route_stops = relationship("RouteStop", back_populates="stop", cascade="all, delete-orphan")

class RouteStop(Base):
    __tablename__ = "route_stops"

    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("routes.id", ondelete="CASCADE"), nullable=False)
    stop_id = Column(Integer, ForeignKey("stops.id", ondelete="CASCADE"), nullable=False)
    sequence_order = Column(Integer, nullable=False)
    distance_from_start_km = Column(Float, default=0.0)
    estimated_time_mins = Column(Integer, default=0)

    # Relationships
    route = relationship("Route", back_populates="route_stops")
    stop = relationship("Stop", back_populates="route_stops")

class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True)
    bus_id = Column(Integer, ForeignKey("buses.id", ondelete="CASCADE"), nullable=False)
    driver_id = Column(Integer, ForeignKey("drivers.id", ondelete="CASCADE"), nullable=False)
    route_id = Column(Integer, ForeignKey("routes.id", ondelete="CASCADE"), nullable=False)
    status = Column(SQLEnum(TripStatus), default=TripStatus.SCHEDULED, nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)

    # Relationships
    bus = relationship("Bus", back_populates="trips")
    driver = relationship("Driver", back_populates="trips")
    route = relationship("Route", back_populates="trips")
    locations = relationship("BusLocation", back_populates="trip", cascade="all, delete-orphan")

class BusLocation(Base):
    __tablename__ = "bus_locations"

    id = Column(Integer, primary_key=True, index=True)
    bus_id = Column(Integer, ForeignKey("buses.id", ondelete="CASCADE"), index=True, nullable=False)
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="SET NULL"), nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    speed_kmh = Column(Float, default=0.0)
    crowd_level = Column(SQLEnum(CrowdLevel), default=CrowdLevel.LOW, nullable=True)
    current_stop_id = Column(Integer, ForeignKey("stops.id", ondelete="SET NULL"), nullable=True)
    next_stop_id = Column(Integer, ForeignKey("stops.id", ondelete="SET NULL"), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    bus = relationship("Bus", back_populates="locations")
    trip = relationship("Trip", back_populates="locations")

class ETAPrediction(Base):
    __tablename__ = "eta_predictions"

    id = Column(Integer, primary_key=True, index=True)
    bus_id = Column(Integer, ForeignKey("buses.id", ondelete="CASCADE"), nullable=False)
    stop_id = Column(Integer, ForeignKey("stops.id", ondelete="CASCADE"), nullable=False)
    predicted_eta_minutes = Column(Float, nullable=False)
    confidence_score = Column(Float, default=0.9)
    model_version = Column(String, default="rf_v1.0")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    bus = relationship("Bus", back_populates="eta_predictions")

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(SQLEnum(AlertSeverity), default=AlertSeverity.INFO, nullable=False)
    route_id = Column(Integer, ForeignKey("routes.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    # Relationships
    route = relationship("Route", back_populates="alerts")

class Favorite(Base):
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    target_type = Column(SQLEnum(FavoriteType), nullable=False)
    target_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="favorites")
