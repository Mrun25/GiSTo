"""
GiSTo backend — FastAPI app. Serves both the Telegram bot (Phase 1) and
the future/present CA dashboard (Phase 2) from one API, per PRD §5.4
("FastAPI ... serves both Telegram and the future dashboard from one API").
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import business, invoice, alert, ca, export, chat
from app.scheduler import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = start_scheduler()
    yield
    scheduler.shutdown()


app = FastAPI(title="GiSTo API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Allow dashboard dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(business.router)
app.include_router(invoice.router)
app.include_router(alert.router)
app.include_router(ca.router)
app.include_router(export.router)
app.include_router(chat.router)


@app.get("/health")
def health():
    return {"status": "ok"}
