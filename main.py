from fastapi import FastAPI, Depends, HTTPException, status
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from datetime import date
from typing import List, Dict, Any

from database import init_db, get_session
from models import Booking
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Meeting Room Booking System")

# 1. Configuration (Time Mapper)
OFFICE_HOURS_MAP = {
    10: "10-11 AM",
    11: "11-12 PM",
    12: "12-1 PM",
    13: "1-2 PM",
    14: "2-3 PM",
    15: "3-4 PM",
    16: "4-5 PM",
    17: "5-6 PM",
    18: "6-7 PM"
}

TOTAL_ROOMS = 10

# Pydantic Schemas for Request/Response
class BookingCreate(BaseModel):
    room_id: int
    booking_date: date
    slot_hour: int
    team_name: str

class SlotStatus(BaseModel):
    time_label: str
    slot_hour: int
    status: str
    team_name: str | None

class RoomSchedule(BaseModel):
    room_id: int
    schedule: List[SlotStatus]

@app.on_event("startup")
async def on_startup():
    await init_db()

# --- Endpoint 2: GET /dashboard-grid ---
@app.get("/dashboard-grid", response_model=List[RoomSchedule])
async def get_dashboard_grid(
    target_date: date, 
    session: AsyncSession = Depends(get_session)
):
    # Step 1: Query DB for ALL bookings on this date (Single Query for efficiency)
    statement = select(Booking).where(Booking.booking_date == target_date)
    result = await session.execute(statement)
    bookings = result.scalars().all()

    # Step 2: Create a lookup dictionary for O(1) access
    # Key: (room_id, slot_hour) -> Value: Booking Object
    booking_map = {
        (b.room_id, b.slot_hour): b for b in bookings
    }

    dashboard_data = []

    # Step 3: Construct the Grid
    for room_id in range(1, TOTAL_ROOMS + 1):
        room_schedule = []
        
        for hour, label in OFFICE_HOURS_MAP.items():
            # Check if this specific slot exists in our DB fetch
            existing_booking = booking_map.get((room_id, hour))
            
            if existing_booking:
                status_entry = SlotStatus(
                    time_label=label,
                    slot_hour=hour,
                    status="occupied",
                    team_name=existing_booking.team_name
                )
            else:
                status_entry = SlotStatus(
                    time_label=label,
                    slot_hour=hour,
                    status="available",
                    team_name=None
                )
            
            room_schedule.append(status_entry)

        dashboard_data.append(RoomSchedule(room_id=room_id, schedule=room_schedule))

    return dashboard_data

# --- Endpoint 3: POST /book-slot ---
@app.post("/book-slot", status_code=status.HTTP_201_CREATED)
async def book_slot(
    booking_data: BookingCreate, 
    session: AsyncSession = Depends(get_session)
):
    # Validation
    if booking_data.room_id < 1 or booking_data.room_id > TOTAL_ROOMS:
        raise HTTPException(status_code=400, detail="Invalid Room ID")
    
    if booking_data.slot_hour not in OFFICE_HOURS_MAP:
        raise HTTPException(status_code=400, detail="Invalid time slot. Office open 10-19")

    new_booking = Booking(
        room_id=booking_data.room_id,
        booking_date=booking_data.booking_date,
        slot_hour=booking_data.slot_hour,
        team_name=booking_data.team_name
    )

    try:
        session.add(new_booking)
        await session.commit()
        await session.refresh(new_booking)
        return {"message": "Booking successful", "id": new_booking.id}
        
    except IntegrityError:
        # This catches the UniqueConstraint violation from PostgreSQL
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Slot already booked for this room and time."
        )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Real project mein "*" unsafe hota hai, par local ke liye OK hai
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)