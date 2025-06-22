from fastapi import FastAPI
from sqlmodel import SQLModel, create_engine
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import models 
from models import Earning
from fastapi import HTTPException
from sqlmodel import Session, select
from models import User
import asyncio
from sse_starlette.sse import EventSourceResponse
from fastapi import Request
from fastapi.staticfiles import StaticFiles
import json
import sqlite3
from sqlalchemy import func




DATABASE_URL = "sqlite:///referral.db"
engine = create_engine(DATABASE_URL, echo=True)

queues: dict[int, asyncio.Queue] = {}

def notify_clients(user_id: int, amount: float, level: int):
    print(f"[notify_clients] Sending {amount} to user {user_id} at level {level}")
    if q := queues.get(user_id):
        q.put_nowait({"amount": amount, "level": level})


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Called before the app starts
    SQLModel.metadata.create_all(engine)
    yield
    # (Optional cleanup on shutdown)


app = FastAPI(lifespan=lifespan)

@app.post("/refer")
def refer_user(referrer_id: int, user_id: int):
    with Session(engine) as session:
        referrer = session.get(User, referrer_id)
        if not referrer:
            return {"error": "Referrer not found"}, 404

        user = session.get(User, user_id)
        if not user:
            return {"error": "User not found"}, 404

        if user.referred_by is not None:
            return {"error": "User already referred"}, 400

        direct_referrals = session.exec(select(User).where(User.referred_by == referrer_id)).all()
        if len(direct_referrals) >= 8:
            return {"error": "Referral limit reached"}, 400

        user.referred_by = referrer_id
        session.add(user)
        session.commit()
        return {"message": "User referred", "user_id": user.id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

@app.post("/user")
def create_user(name: str):
    with Session(engine) as session:
        user = User(name=name)
        session.add(user)
        session.commit()
        session.refresh(user)
    return {"user_id": user.id}

@app.post("/purchase")
def make_purchase(buyer_id: int, amount: float):
        if amount < 1000:
            return {"message": "No commissions for purchases below ₹1000."}

        distributed = []
        with Session(engine) as session:
            buyer = session.get(User, buyer_id)
            if not buyer:
                raise HTTPException(404, "Buyer not found")

            # Log transaction
            session.add(models.Transaction(
                user_id=buyer_id,
                amount=amount,
                is_valid=True,
                note="Auto-logged from purchase API"
            ))

            parent = session.get(User, buyer.referred_by) if buyer.referred_by else None
            if parent and parent.is_active:
                total_earned = session.exec(
                    select(func.sum(Earning.amount)).where(Earning.user_id == parent.id)
                ).one() or 0

                if total_earned < 1000:
                    profit1 = round(amount * 0.05, 2)
                    if total_earned + profit1 > 1000:
                        profit1 = round(1000 - total_earned, 2)
                    session.add(Earning(user_id=parent.id, source_user_id=buyer.id, level=1, amount=profit1))
                    distributed.append((parent.id, profit1, 1))

            elif parent:
                print(f"[purchase] Skipping inactive parent user {parent.id}")

            gp = session.get(User, parent.referred_by) if parent else None
            if gp and gp.is_active:
                total_earned = session.exec(
                    select(func.sum(Earning.amount)).where(Earning.user_id == gp.id)
                ).one() or 0

                if total_earned < 1000:
                    profit2 = round(amount * 0.01, 2)
                    if total_earned + profit2 > 1000:
                        profit2 = round(1000 - total_earned, 2)
                    session.add(Earning(user_id=gp.id, source_user_id=buyer.id, level=2, amount=profit2))
                    distributed.append((gp.id, profit2, 2))

            elif gp:
                print(f"[purchase] Skipping inactive grandparent user {gp.id}")

            session.commit()

        # Broadcast via SSE
        for (uid, amt, lvl) in distributed:
            notify_clients(uid, amt, lvl)

        return {"message": "Purchase processed", "distributed": distributed}


@app.get("/referrals/{user_id}")
def get_referrals(user_id: int):
    with Session(engine) as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        direct = session.exec(select(User).where(User.referred_by == user_id)).all()
        indirect = []
        for u in direct:
            children = session.exec(select(User).where(User.referred_by == u.id)).all()
            indirect.extend(children)

    return {
        "user_id": user_id,
        "direct_referrals": [
            {"id": u.id, "name": u.name, "is_active": u.is_active} for u in direct
        ],
        "indirect_referrals": [
            {"id": u.id, "name": u.name, "via": u.referred_by, "is_active": u.is_active} for u in indirect
        ]
    }
@app.get("/leaderboard")
def get_leaderboard():
    with Session(engine) as session:
        from models import Earning, User
        results = (
            session.query(User.id, User.name, func.sum(Earning.amount).label("total"))
            .join(Earning, Earning.user_id == User.id)
            .group_by(User.id)
            .order_by(func.sum(Earning.amount).desc())
            .limit(10)
            .all()
        )

    return [
        {"user_id": user_id, "name": name, "total_earnings": round(total, 2)}
        for user_id, name, total in results
    ]


@app.get("/earnings/{user_id}")
def get_earnings(user_id: int):
    with Session(engine) as session:
        earnings = session.exec(select(Earning).where(Earning.user_id == user_id)).all()
        if earnings is None:
            raise HTTPException(status_code=404, detail="User not found or no earnings")

    total = sum(e.amount for e in earnings)
    by_level = {
        1: sum(e.amount for e in earnings if e.level == 1),
        2: sum(e.amount for e in earnings if e.level == 2),
    }
    breakdown = [
        {"source_user_id": e.source_user_id, "level": e.level, "amount": e.amount, "timestamp": e.timestamp}
        for e in earnings
    ]

    return {
        "user_id": user_id,
        "total_earnings": total,
        "earnings_by_level": by_level,
        "details": breakdown
    }

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/events/{user_id}")
async def events(user_id: int, request: Request):
    q = asyncio.Queue()
    queues[user_id] = q

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                data = await q.get()
                # Serialize the data dict to a JSON string
                yield {"data": json.dumps(data)}
        finally:
            queues.pop(user_id, None)

    return EventSourceResponse(event_generator())

#@app.get("/debug/transactions")
#def debug_tx():
#    with Session(engine) as session:
#        txs = session.exec(select(models.Transaction)).all()
#        return [tx.dict() for tx in txs]


#@app.get("/debug/schema")
#def get_user_schema():
#    conn = sqlite3.connect("referral.db")
#    cursor = conn.cursor()
#    cursor.execute("PRAGMA table_info('user')")
#    columns = cursor.fetchall()  # rows like (cid, #name, type, notnull, dflt_value, pk)
#    conn.close()
#    return {"user_table_info": columns}

@app.patch("/user/{user_id}/deactivate")
def deactivate_user(user_id: int):
    with Session(engine) as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.is_active = False
        session.add(user)
        session.commit()
    return {"message": f"User {user_id} deactivated."}

@app.patch("/user/{user_id}/reactivate")
def reactivate_user(user_id: int):
    with Session(engine) as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.is_active = True
        session.add(user)
        session.commit()
    return {"message": f"User {user_id} reactivated."}


    
@app.get("/")
def home():
    return {"message": "Referral System is up and running!"}
