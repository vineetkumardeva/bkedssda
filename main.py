from fastapi import FastAPI
from sqlmodel import SQLModel, create_engine
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import models  # ensures your User and Earning models are registered

from sqlmodel import Session, select
from models import User

DATABASE_URL = "sqlite:///referral.db"
engine = create_engine(DATABASE_URL, echo=True)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Called before the app starts
    SQLModel.metadata.create_all(engine)
    yield
    # (Optional cleanup on shutdown)


app = FastAPI(lifespan=lifespan)

@app.post("/refer")
def refer_user(referrer_id: int, new_user_name: str):
    with Session(engine) as session:
        referrer = session.get(User, referrer_id)
        if not referrer:
            return {"error": "Referrer not found"}, 404
        statement = select(User).where(User.referred_by == referrer_id)
        count = session.execute(statement).scalars().all()
        if len(count) >= 8:
            return {"error": "Referral limit reached"}, 400
        new_user = User(name=new_user_name, referred_by=referrer_id)
        session.add(new_user)
        session.commit()
        return {"message": "User referred", "new_user_id": new_user.id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

    
@app.get("/")
def home():
    return {"message": "Referral System is up and running!"}
