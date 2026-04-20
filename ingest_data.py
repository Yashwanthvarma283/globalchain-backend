import kagglehub
import pandas as pd
from sqlalchemy.orm import Session
from database import engine, Base, SessionLocal
from models import Vendor, SupplyRoute, User
from auth import get_password_hash
import os

def initialize_database():
    print("Creating DB tables...")
    Base.metadata.create_all(bind=engine)

def seed_users(db: Session):
    print("Seeding test users...")
    
    admin = db.query(User).filter(User.email == "test.admin@gmail.com").first()
    if not admin:
        admin = User(
            email="test.admin@gmail.com",
            hashed_password=get_password_hash("123456"),
            role="Admin",
            status="Approved"
        )
        db.add(admin)
        
    user = db.query(User).filter(User.email == "test.user@gmail.com").first()
    if not user:
        user = User(
            email="test.user@gmail.com",
            hashed_password=get_password_hash("123456"),
            role="Buyer",
            status="Approved"
        )
        db.add(user)
    
    db.commit()
    print("Users seeded successfully.")

def ingest_kaggle_data(db: Session):
    print("Downloading dataset from Kaggle...")
    try:
        path = kagglehub.dataset_download("shashwatwork/dataco-smart-supply-chain-for-big-data-analysis")
        print(f"Dataset downloaded to: {path}")
    except Exception as e:
        print(f"Error downloading from Kaggle API: {e}")
        return

    csv_file = None
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith('.csv'):
                csv_file = os.path.join(root, file)
                break
        if csv_file:
            break
            
    if not csv_file:
        print("CSV file not found in the downloaded dataset.")
        return
        
    print(f"Loading data from {csv_file}...")
    
    # Read a sample to avoid overloading local DB during dev
    df = pd.read_csv(csv_file, encoding='latin1', nrows=100)
    
    # We will map customer locations to Buyer, and Order Country/City to Vendors roughly, 
    # but the real dataset lacks explicit lat/lng sometimes. 
    # Let's seed dummy lat/lngs for the vendors based on Order Country.
    # For now, we will create 5 synthetic vendors to render on the globe
    
    vendor_locations = [
        {"name": "Shenzhen Electronics Hub", "lat": 22.5431, "lng": 114.0579, "risk_level": "High"},
        {"name": "Rotterdam Port Logistics", "lat": 51.9244, "lng": 4.4777, "risk_level": "Safe"},
        {"name": "Texas Advanced Mfg", "lat": 31.9686, "lng": -99.9018, "risk_level": "Medium"},
        {"name": "London Supply Co", "lat": 51.5074, "lng": -0.1278, "risk_level": "Safe"},
        {"name": "Mumbai Textiles Facility", "lat": 19.0760, "lng": 72.8777, "risk_level": "High"},
    ]
    
    existing_vendors = db.query(Vendor).count()
    if existing_vendors == 0:
        for v in vendor_locations:
            vendor = Vendor(
                name=v["name"], 
                lat=v["lat"], 
                lng=v["lng"], 
                risk_level=v["risk_level"],
                risk_score=0.8 if v["risk_level"] == "High" else 0.1
            )
            db.add(vendor)
        db.commit()
        print("Inserted vendor geolocations to render on Globe.")
    else:
        print("Vendors already seeded.")

def run_seed():
    initialize_database()
    db = SessionLocal()
    try:
        seed_users(db)
        ingest_kaggle_data(db)
    finally:
        db.close()

if __name__ == "__main__":
    run_seed()
