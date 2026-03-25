import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.database import Base, _async_engine
from app.models import user, account, audience

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with _async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    lifespan=lifespan,
)

origins = [
    "http://localhost:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.v1 import auth, accounts, audience

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(accounts.router, prefix="/api/v1/accounts", tags=["accounts"])
app.include_router(audience.router, tags=["audience"])

frontend_dist = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "traffsoft-frontend",
    "dist",
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def root():
    index_path = os.path.join(frontend_dist, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "TraffSoft API", "docs": "/docs"}


if os.path.exists(frontend_dist):
    assets_path = os.path.join(frontend_dist, "assets")
    if os.path.exists(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")
