# api/app/main.py
import os
from datetime import date, timedelta
from typing import Optional, Dict

from fastapi import FastAPI, HTTPException, Response, Cookie, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from passlib.hash import pbkdf2_sha256 as hasher
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# DB konekcija (u docker-compose mora biti postgresql+psycopg://...)
DATABASE_URL = os.getenv("DATABASE_URL")
engine: Engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Najjednostavnije sesije u memoriji (za HA koristi Redis/DB)
SESSIONS: Dict[str, str] = {}

app = FastAPI(title="SeatApp API (Local Auth / PBKDF2)")

# CORS
origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != [''] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- pomoćne funkcije ---
def get_user_by_upn(upn: str):
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT id, upn, name, dept, roles, password_hash FROM app_user WHERE upn=:u"),
            {"u": upn},
        ).mappings().first()
        return dict(row) if row else None

def get_user_by_id(uid: int):
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT id, upn, name, dept, roles FROM app_user WHERE id=:i"),
            {"i": uid},
        ).mappings().first()
        return dict(row) if row else None

# --- modeli ---
class LoginBody(BaseModel):
    username: str
    password: str

# --- auth rute ---
@app.post("/api/login")
def login(body: LoginBody, response: Response):
    user = get_user_by_upn(body.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not hasher.verify(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # kreiraj session cookie
    import secrets
    sid = secrets.token_urlsafe(32)
    SESSIONS[sid] = str(user["id"])
    response.set_cookie("seatapp_session", sid, httponly=True, samesite="lax", path="/")

    return {
        "id": user["id"],
        "upn": user["upn"],
        "name": user["name"],
        "dept": user["dept"],
        "roles": user["roles"],
    }

@app.post("/api/logout")
def logout(response: Response, seatapp_session: Optional[str] = Cookie(default=None)):
    if seatapp_session and seatapp_session in SESSIONS:
        del SESSIONS[seatapp_session]
    response.delete_cookie("seatapp_session", path="/")
    return {"ok": True}

def auth_user(seatapp_session: Optional[str] = Cookie(default=None)):
    if not seatapp_session or seatapp_session not in SESSIONS:
        raise HTTPException(status_code=401, detail="Not authenticated")
    uid = int(SESSIONS[seatapp_session])
    user = get_user_by_id(uid)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid session")
    return user

@app.get("/api/me")
def me(user=Depends(auth_user)):
    return user

# --- health ---
@app.get("/api/health")
def health():
    with engine.begin() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}

# --- floors & seats ---
@app.get("/api/floors")
def floors(user=Depends(auth_user)):
    with engine.begin() as conn:
        rows = conn.execute(text("SELECT id, name FROM floor ORDER BY id")).mappings().all()
        return [dict(r) for r in rows]

@app.get("/api/seats")
def seats(floorId: int, user=Depends(auth_user)):
    sql = text("""
      SELECT s.id, s.code, z.floor_id
      FROM seat s
      JOIN zone z ON s.zone_id = z.id
      WHERE z.floor_id = :f
      ORDER BY s.id
    """)
    with engine.begin() as conn:
        rows = conn.execute(sql, {"f": floorId}).mappings().all()
        return [dict(r) for r in rows]

# --- reporting helpers ---
def _range_dates(period: str):
    today = date.today()
    if period == "weekly":
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
    elif period == "monthly":
        start = today.replace(day=1)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end = start.replace(month=start.month + 1, day=1) - timedelta(days=1)
    elif period == "yearly":
        start = date(today.year, 1, 1)
        end = date(today.year, 12, 31)
    else:
        raise ValueError("bad period")
    return start, end

def _attendance_counts(user_id: int, start: date, end: date):
    sql = text("""
      SELECT status, COUNT(*) AS c
      FROM booking
      WHERE user_id = :u AND date BETWEEN :s AND :e
      GROUP BY status
    """)
    with engine.begin() as conn:
        rows = conn.execute(sql, {"u": user_id, "s": start, "e": end}).mappings().all()
    counts = {r["status"]: r["c"] for r in rows}
    office = counts.get("confirmed", 0) + counts.get("checked_in", 0) + counts.get("held", 0)
    remote = counts.get("remote", 0)
    noshow = counts.get("no_show", 0)
    return {"office": office, "remote": remote, "no_show": noshow}

# --- reports ---
@app.get("/api/reports/weekly")
def weekly(user_id: Optional[int] = None, user=Depends(auth_user)):
    uid = user_id or user["id"]
    start, end = _range_dates("weekly")
    return {"range": {"from": start.isoformat(), "to": end.isoformat()},
            "data": _attendance_counts(uid, start, end)}

@app.get("/api/reports/monthly")
def monthly(user_id: Optional[int] = None, user=Depends(auth_user)):
    uid = user_id or user["id"]
    start, end = _range_dates("monthly")
    return {"range": {"from": start.isoformat(), "to": end.isoformat()},
            "data": _attendance_counts(uid, start, end)}

@app.get("/api/reports/yearly")
def yearly(user_id: Optional[int] = None, user=Depends(auth_user)):
    uid = user_id or user["id"]
    start, end = _range_dates("yearly")
    return {"range": {"from": start.isoformat(), "to": end.isoformat()},
            "data": _attendance_counts(uid, start, end)}
