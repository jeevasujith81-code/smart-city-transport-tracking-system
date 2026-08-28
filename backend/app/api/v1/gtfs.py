import io
import csv
import zipfile
from datetime import datetime
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.models import Route, Stop, RouteStop, Trip, Bus

router = APIRouter()

@router.get("/export", summary="Export City Transit Schedule as standard GTFS Zip Archive")
def export_gtfs_zip(db: Session = Depends(get_db)):
    """
    Generates a compliant GTFS (General Transit Feed Specification) ZIP package
    containing agency.txt, stops.txt, routes.txt, trips.txt, stop_times.txt, and calendar.txt
    for consumption by Google Maps, Apple Maps, or Transit App.
    """
    zip_buffer = io.BytesIO()

    routes = db.query(Route).all()
    stops = db.query(Stop).all()
    route_stops = db.query(RouteStop).all()
    trips = db.query(Trip).all()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        
        # 1. agency.txt
        agency_io = io.StringIO()
        agency_writer = csv.writer(agency_io)
        agency_writer.writerow(["agency_id", "agency_name", "agency_url", "agency_timezone", "agency_lang"])
        agency_writer.writerow(["AGENCY-CITYTRACK", "CityTrack Small City Transit Authority", "http://localhost:8000/app/", "Asia/Kolkata", "en"])
        zip_file.writestr("agency.txt", agency_io.getvalue())

        # 2. stops.txt
        stops_io = io.StringIO()
        stops_writer = csv.writer(stops_io)
        stops_writer.writerow(["stop_id", "stop_code", "stop_name", "stop_lat", "stop_lon"])
        for s in stops:
            stops_writer.writerow([s.id, s.code, s.stop_name, s.latitude, s.longitude])
        zip_file.writestr("stops.txt", stops_io.getvalue())

        # 3. routes.txt
        routes_io = io.StringIO()
        routes_writer = csv.writer(routes_io)
        routes_writer.writerow(["route_id", "agency_id", "route_short_name", "route_long_name", "route_type"])
        for r in routes:
            routes_writer.writerow([r.id, "AGENCY-CITYTRACK", r.route_code, r.route_name, "3"]) # 3 = Bus
        zip_file.writestr("routes.txt", routes_io.getvalue())

        # 4. calendar.txt
        calendar_io = io.StringIO()
        calendar_writer = csv.writer(calendar_io)
        calendar_writer.writerow(["service_id", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "start_date", "end_date"])
        calendar_writer.writerow(["DAILY_SERVICE", "1", "1", "1", "1", "1", "1", "1", "20260101", "20261231"])
        zip_file.writestr("calendar.txt", calendar_io.getvalue())

        # 5. trips.txt
        trips_io = io.StringIO()
        trips_writer = csv.writer(trips_io)
        trips_writer.writerow(["route_id", "service_id", "trip_id", "trip_headsign"])
        for t in trips:
            trips_writer.writerow([t.route_id, "DAILY_SERVICE", t.id, f"Bus #{t.bus_id} Trip"])
        zip_file.writestr("trips.txt", trips_io.getvalue())

        # 6. stop_times.txt
        st_io = io.StringIO()
        st_writer = csv.writer(st_io)
        st_writer.writerow(["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"])
        for rs in route_stops:
            mins = rs.estimated_time_mins or 0
            hrs = 6 + (mins // 60)
            rem_mins = mins % 60
            arr_str = f"{hrs:02d}:{rem_mins:02d}:00"
            st_writer.writerow([rs.route_id, arr_str, arr_str, rs.stop_id, rs.sequence_order])
        zip_file.writestr("stop_times.txt", st_io.getvalue())

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=gtfs_citytrack.zip"}
    )
