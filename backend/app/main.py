from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.bgg import router as bgg_router
from app.api.collection import router as collection_router
from app.api.friends import router as friends_router
from app.api.groups import invites_router
from app.api.groups import router as groups_router
from app.api.guest import router as guest_router
from app.api.locations import router as locations_router
from app.api.occurrences import router as occurrences_router
from app.api.polls import router as polls_router
from app.api.public import router as public_router
from app.api.series import router as series_router
from app.api.users import router as users_router
from app.config import settings

app = FastAPI(
    title="Game On Tabletop API",
    description=(
        "REST API for Game On Tabletop — a platform for organising tabletop game nights, "
        "tracking game collections, scheduling events, and managing group RSVPs."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router = APIRouter(prefix="/api")

api_router.include_router(auth_router)
api_router.include_router(bgg_router)
api_router.include_router(users_router)
api_router.include_router(groups_router)
api_router.include_router(invites_router)
api_router.include_router(locations_router)
api_router.include_router(series_router)
api_router.include_router(occurrences_router)
api_router.include_router(collection_router)
api_router.include_router(friends_router)
api_router.include_router(polls_router)
api_router.include_router(guest_router)
api_router.include_router(public_router)


@api_router.get("/", include_in_schema=False)
async def root():
    return {"message": "Hello World"}


@api_router.get("/health", summary="Health check", tags=["health"])
async def health():
    return {"status": "ok"}


app.include_router(api_router)
