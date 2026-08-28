import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.core.db import SessionLocal, Base, engine
from app.core.security import get_password_hash
from app.models.models import (
    User, UserRole, Driver, Bus, BusStatus, Route, Stop, RouteStop, 
    Trip, TripStatus, BusLocation, Alert, AlertSeverity, ETAPrediction
)

def seed_database():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        # Check if already seeded
        if db.query(User).filter(User.email == "admin@citytrack.com").first():
            print("Database already seeded. Skipping...")
            return

        print("Seeding CityTrack Database with production-style demo data...")

        # 1. Create Admin User
        admin_user = User(
            email="admin@citytrack.com",
            hashed_password=get_password_hash("Admin@123"),
            full_name="System Administrator",
            role=UserRole.ADMIN
        )
        db.add(admin_user)

        # 2. Create Demo Passenger User
        passenger_user = User(
            email="passenger@citytrack.com",
            hashed_password=get_password_hash("Passenger@123"),
            full_name="Alex Mercer",
            role=UserRole.PASSENGER
        )
        db.add(passenger_user)

        # 3. Create Drivers & Users
        driver_users = []
        drivers = []
        for i in range(1, 11):
            d_user = User(
                email=f"driver{i}@citytrack.com",
                hashed_password=get_password_hash("Driver@123"),
                full_name=f"Driver John Doe #{i}",
                role=UserRole.DRIVER
            )
            db.add(d_user)
            db.flush()

            driver = Driver(
                user_id=d_user.id,
                license_number=f"DL-CITY-{202600 + i}",
                phone=f"+1-555-01{i:02d}",
                status="ON_TRIP" if i <= 6 else "AVAILABLE"
            )
            db.add(driver)
            drivers.append(driver)

        db.flush()

        # 4. Create 25 Bus Stops
        stops_data = [
            ("Central Railway Station", "ST-001", 12.9716, 77.5946, "Central Terminal"),
            ("City Town Hall", "ST-002", 12.9634, 77.5855, "Downtown"),
            ("Main Market Circle", "ST-003", 12.9550, 77.5780, "Market Square"),
            ("National College Corner", "ST-004", 12.9430, 77.5720, "South District"),
            ("Jayanagar 4th Block", "ST-005", 12.9298, 77.5826, "Residential Hub"),
            ("JP Nagar Metro", "ST-006", 12.9080, 77.5750, "Metro Junction"),
            ("Bannerghatta Gate", "ST-007", 12.8900, 77.5980, "South Suburbs"),
            ("Electronic City Gate 1", "ST-008", 12.8452, 77.6602, "IT Corridor"),
            ("Silk Board Flyover", "ST-009", 12.9172, 77.6228, "Central Junction"),
            ("Koramangala Bus Station", "ST-010", 12.9352, 77.6245, "Tech District"),
            ("Indiranagar 100ft Road", "ST-011", 12.9784, 77.6408, "East District"),
            ("MG Road Metro Station", "ST-012", 12.9756, 77.6066, "Business Core"),
            ("Trinity Circle", "ST-013", 12.9725, 77.6180, "Business Core"),
            ("Domlur Flyover", "ST-014", 12.9600, 77.6380, "IT Park"),
            ("Marathahalli Bridge", "ST-015", 12.9560, 77.6980, "Outer Ring Road"),
            ("Whitefield ITPL Gate", "ST-016", 12.9850, 77.7280, "Tech Hub"),
            ("HSR Layout Sector 1", "ST-017", 12.9120, 77.6450, "South East"),
            ("BTM Layout Water Tank", "ST-018", 12.9166, 77.6101, "South District"),
            ("Banashankari Bus Terminal", "ST-019", 12.9250, 77.5670, "West Terminal"),
            ("Malleswaram 8th Cross", "ST-020", 12.9980, 77.5710, "North West"),
            ("Yeshwanthpur Junction", "ST-021", 13.0280, 77.5450, "North Terminal"),
            ("Hebbal Bus Stop", "ST-022", 13.0350, 77.5970, "North Gate"),
            ("Yelahanka Satellite Town", "ST-023", 13.1000, 77.5960, "North Suburbs"),
            ("Airport Expressway Gate", "ST-024", 13.1900, 77.6300, "North Corridor"),
            ("International Airport T1", "ST-025", 13.1986, 77.7066, "Airport Terminal"),
        ]

        stops = []
        for name, code, lat, lng, area in stops_data:
            s = Stop(stop_name=name, code=code, latitude=lat, longitude=lng, city_area=area)
            db.add(s)
            stops.append(s)

        db.flush()

        # 5. Create 5 Routes with polylines
        routes_def = [
            {
                "name": "Route 101 - Central Metro Express",
                "code": "R101",
                "origin": "Central Railway Station",
                "destination": "Electronic City Gate 1",
                "distance": 18.5,
                "stops": [0, 1, 2, 3, 4, 5, 6, 7] # indices in stops list
            },
            {
                "name": "Route 202 - City Center & Tech Loop",
                "code": "R202",
                "origin": "Central Railway Station",
                "destination": "Indiranagar 100ft Road",
                "distance": 12.0,
                "stops": [0, 11, 12, 13, 10, 9]
            },
            {
                "name": "Route 303 - IT Corridor Shuttle",
                "code": "R303",
                "origin": "Koramangala Bus Station",
                "destination": "Whitefield ITPL Gate",
                "distance": 22.4,
                "stops": [9, 8, 16, 13, 14, 15]
            },
            {
                "name": "Route 404 - Airport Direct Flyer",
                "code": "R404",
                "origin": "Central Railway Station",
                "destination": "International Airport T1",
                "distance": 34.0,
                "stops": [0, 11, 21, 22, 23, 24]
            },
            {
                "name": "Route 505 - North-South Suburban Connector",
                "code": "R505",
                "origin": "Banashankari Bus Terminal",
                "destination": "Yeshwanthpur Junction",
                "distance": 16.8,
                "stops": [18, 4, 3, 2, 1, 19, 20]
            }
        ]

        routes = []
        for r_info in routes_def:
            r_stops = [stops[idx] for idx in r_info["stops"]]
            coords = [[s.latitude, s.longitude] for s in r_stops]
            
            r = Route(
                route_name=r_info["name"],
                route_code=r_info["code"],
                origin=r_info["origin"],
                destination=r_info["destination"],
                total_distance_km=r_info["distance"],
                polyline_coords=json.dumps(coords)
            )
            db.add(r)
            db.flush()
            routes.append(r)

            # Map RouteStops
            for idx, s in enumerate(r_stops):
                rs = RouteStop(
                    route_id=r.id,
                    stop_id=s.id,
                    sequence_order=idx + 1,
                    distance_from_start_km=round((idx / (len(r_stops) - 1)) * r_info["distance"], 1) if len(r_stops) > 1 else 0.0,
                    estimated_time_mins=idx * 6
                )
                db.add(rs)

        db.flush()

        # 6. Create 12 Buses
        buses = []
        for i in range(1, 13):
            route_assigned = routes[(i - 1) % len(routes)]
            driver_assigned = drivers[i - 1] if i <= len(drivers) else None
            
            b = Bus(
                bus_number=f"BUS-{100 + i}",
                capacity=45 if i % 2 == 0 else 55,
                model="Volvo B7R Smart Transit" if i % 3 == 0 else "Tata Electric Cityliner",
                status=BusStatus.ACTIVE if i <= 10 else BusStatus.MAINTENANCE,
                assigned_route_id=route_assigned.id,
                assigned_driver_id=driver_assigned.id if driver_assigned else None
            )
            db.add(b)
            db.flush()
            buses.append(b)
            if driver_assigned:
                driver_assigned.assigned_bus_id = b.id

        db.flush()

        # 7. Create Active Trips & Live Location Records
        for i in range(1, 8):
            b = buses[i - 1]
            d = drivers[i - 1]
            r = routes[(i - 1) % len(routes)]

            trip = Trip(
                bus_id=b.id,
                driver_id=d.id,
                route_id=r.id,
                status=TripStatus.IN_PROGRESS,
                start_time=datetime.utcnow() - timedelta(minutes=15 * i)
            )
            db.add(trip)
            db.flush()

            # Find origin stop coords
            r_stops = db.query(RouteStop).filter(RouteStop.route_id == r.id).order_by(RouteStop.sequence_order).all()
            first_stop = db.query(Stop).get(r_stops[0].stop_id)
            next_stop = db.query(Stop).get(r_stops[1].stop_id) if len(r_stops) > 1 else first_stop

            # Slight offset for live moving simulation
            lat_offset = (i * 0.003)
            lng_offset = (i * 0.002)

            loc = BusLocation(
                bus_id=b.id,
                trip_id=trip.id,
                latitude=first_stop.latitude + lat_offset,
                longitude=first_stop.longitude + lng_offset,
                speed_kmh=35.5 + (i * 2.0),
                current_stop_id=first_stop.id,
                next_stop_id=next_stop.id,
                timestamp=datetime.utcnow()
            )
            db.add(loc)

            # ETA prediction record
            eta = ETAPrediction(
                bus_id=b.id,
                stop_id=next_stop.id,
                predicted_eta_minutes=6.5 + i,
                confidence_score=0.92,
                model_version="rf_v1.0"
            )
            db.add(eta)

        # 8. Create Service Alerts
        alerts_data = [
            ("Heavy Traffic on Outer Ring Road", "Expect 10-15 min delays on Route 303 near Marathahalli due to road construction.", AlertSeverity.WARNING, routes[2].id),
            ("New Electric Buses Deployed", "Route 101 now features 100% zero-emission electric buses with free Wi-Fi.", AlertSeverity.INFO, routes[0].id),
            ("Airport Expressway Clearance", "Route 404 running on schedule with express non-stop travel times.", AlertSeverity.INFO, routes[3].id),
            ("Route 505 Minor Detour", "Stop #3 temporarily shifted 100m north due to sewer maintenance.", AlertSeverity.WARNING, routes[4].id)
        ]

        for title, desc, sev, r_id in alerts_data:
            a = Alert(
                title=title,
                description=desc,
                severity=sev,
                route_id=r_id,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=3)
            )
            db.add(a)

        db.commit()
        print("Database successfully seeded!")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
