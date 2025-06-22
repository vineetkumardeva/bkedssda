from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from sqlalchemy import Boolean


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    referred_by: Optional[int] = Field(default=None, foreign_key="user.id")

    is_active: bool = Field(default=True, sa_column_kwargs={"nullable": False})  # ✅ New field

    # Relationships for self-join
    referrals: List["User"] = Relationship(back_populates="referrer")
    referrer: Optional["User"] = Relationship(
        back_populates="referrals",
        sa_relationship_kwargs={"remote_side": "User.id"}
    )

class Earning(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    source_user_id: int = Field(foreign_key="user.id")
    level: int  # 1 = direct, 2 = indirect
    amount: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    amount: float
    is_valid: bool
    note: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

