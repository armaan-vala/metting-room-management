from typing import Optional
from datetime import date
from sqlmodel import SQLModel, Field
from sqlalchemy import UniqueConstraint

class Booking(SQLModel, table=True):
    __tablename__ = "bookings"
    __table_args__ = (
        # CRITICAL: Database-level protection against double booking
        UniqueConstraint("room_id", "booking_date", "slot_hour", name="unique_booking_slot"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    room_id: int = Field(index=True)
    booking_date: date = Field(index=True)
    slot_hour: int  # 10, 11, ... 18
    team_name: str