from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.buses import router as buses_router
from app.api.v1.routes import router as routes_router
from app.api.v1.stops import router as stops_router
from app.api.v1.drivers import router as drivers_router
from app.api.v1.trips import router as trips_router
from app.api.v1.eta import router as eta_router
from app.api.v1.alerts import router as alerts_router
from app.api.v1.favorites import router as favorites_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.websocket import router as websocket_router
from app.api.v1.gtfs import router as gtfs_router
from app.api.v1.planner import router as planner_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(buses_router)
api_router.include_router(routes_router)
api_router.include_router(stops_router)
api_router.include_router(drivers_router)
api_router.include_router(trips_router)
api_router.include_router(eta_router)
api_router.include_router(alerts_router)
api_router.include_router(favorites_router)
api_router.include_router(analytics_router)
api_router.include_router(websocket_router)
api_router.include_router(planner_router)
api_router.include_router(gtfs_router, prefix="/gtfs", tags=["GTFS Export"])


