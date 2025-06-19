from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    referred_by: Optional[int] = Field(default=None, foreign_key="user.id")
    # Relationship for SQLite-friendly self-join
    referrals: List["User"] = Relationship(back_populates="referrer")
    referrer: Optional["User"] = Relationship(back_populates="referrals", sa_relationship_kwargs={"remote_side": "User.id"})

class Earning(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    source_user_id: int = Field(foreign_key="user.id")
    level: int  # 1 = direct, 2 = indirect
    amount: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
