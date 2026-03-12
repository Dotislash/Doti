from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.automation.event_queue import EventQueue
from app.automation.routines import RoutineManager
from app.api.rest.routes import router as rest_router, set_stores, set_doti_config
from app.api.ws.router import router as ws_router, _get_store, _get_thread_store
from app.core.config.loader import load_config


@asynccontextmanager
async def lifespan(app: FastAPI):
    set_stores(_get_store(), _get_thread_store())
    doti_config = load_config()
    set_doti_config(doti_config)
    queue = EventQueue()
    manager = RoutineManager(queue)
    app.state.event_queue = queue
    app.state.routine_manager = manager
    await manager.start()
    try:
        yield
    finally:
        await manager.stop()


app = FastAPI(title="doti-backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ws_router)
app.include_router(rest_router)
