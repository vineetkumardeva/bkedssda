from fastapi import FastAPI
from sqlmodel import SQLModel, create_engine
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import models  # ensures your User and Earning models are registered

DATABASE_URL = "sqlite:///referral.db"
engine = create_engine(DATABASE_URL, echo=True)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Called before the app starts
    SQLModel.metadata.create_all(engine)
    yield
    # (Optional cleanup on shutdown)


app = FastAPI(lifespan=lifespan)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

    
@app.get("/")
def home():
    return {"message": "Referral System is up and running!"}
