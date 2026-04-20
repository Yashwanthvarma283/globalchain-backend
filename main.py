from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import models
from database import engine, get_db
from auth import verify_password, create_access_token, get_password_hash
from live_data import update_live_status

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="GlobalChain API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- Schemas ---
class SignupRequest(BaseModel):
    email: str
    password: str
    role: str = "Buyer"
    company: str = ""

# --- Auth Endpoints ---
@app.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password", headers={"WWW-Authenticate": "Bearer"})
    if user.status != "Approved":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is pending admin approval.")
    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer", "role": user.role}

@app.post("/signup")
def signup(request: SignupRequest, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == request.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered.")
    if request.role not in ["Buyer", "Supplier"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be Buyer or Supplier.")
    user = models.User(
        email=request.email,
        hashed_password=get_password_hash(request.password),
        role=request.role,
        status="Pending"
    )
    db.add(user)
    db.commit()
    return {"message": "Signup request submitted. Awaiting admin approval.", "status": "Pending"}

# --- Admin Endpoints ---
@app.get("/admin/users")
def get_all_users(db: Session = Depends(get_db)):
    users = db.query(models.User).all()
    return {"users": [{"id": u.id, "email": u.email, "role": u.role, "status": u.status} for u in users]}

@app.post("/admin/users/{user_id}/approve")
def approve_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    user.status = "Approved"
    db.commit()
    return {"message": f"User {user.email} approved."}

@app.post("/admin/users/{user_id}/reject")
def reject_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    user.status = "Rejected"
    db.commit()
    return {"message": f"User {user.email} rejected."}

# --- Data Endpoints ---
@app.get("/")
def read_root():
    return {"message": "Welcome to GlobalChain API"}

@app.get("/api/globe-data")
def get_globe_data(db: Session = Depends(get_db)):
    vendors = db.query(models.Vendor).all()
    return {"vendors": [{"id": v.id, "name": v.name, "lat": v.lat, "lng": v.lng, "risk_level": v.risk_level} for v in vendors]}

@app.get("/api/live-status")
async def get_live_status():
    return await update_live_status()

