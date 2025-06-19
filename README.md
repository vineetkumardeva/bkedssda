Multi-Level Referral System 
A backend system for tracking multi-level referral earnings, built with FastAPI,SQLModel,SQLite and hosted on Replit.

```bash
git clone https://github.com/vineetkumardeva/bkedssda.git
cd bkedssda
python3 -m venv venv
source venv/bin/activate 
pip install -r requirements.txt

#run 
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Files
models.py:
Defines database tables:
User table supports referral hierarchy
Earning table tracks earning events

main.py:
Sets up FastAPI app with lifespan-based DB table creation and Root GET / endpoint to verify app is running

requirements.txt – Lists dependencies (fastapi, uvicorn, sqlmodel)

Referral Logic (/refer Endpoint) Allows users to refer up to 8 direct referrals.

Endpoint: POST /refer
Query Parameters:

referrer_id (int) – ID of the referring user

new_user_name (string) – Name for the new user

Possible Responses:
200 OK = json{ "message": "User referred", "new_user_id": 2 }
404 Not Found = json{ "detail": "Referrer not found" }
400 Bad Request = json{ "detail": "Referral limit reached" }
