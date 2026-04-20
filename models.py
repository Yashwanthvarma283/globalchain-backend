from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="Buyer") # "Admin", "Buyer", "Supplier"
    status = Column(String, default="Pending") # "Pending", "Approved", "Suspended"

class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    lat = Column(Float)
    lng = Column(Float)
    risk_level = Column(String, default="Safe") # "Safe", "Medium", "High"
    risk_score = Column(Float, default=0.0)

class SupplyRoute(Base):
    __tablename__ = "supply_routes"

    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"))
    buyer_id = Column(Integer, ForeignKey("users.id"))
    
    vendor = relationship("Vendor")
    buyer = relationship("User")
