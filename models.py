from sqlalchemy import Column, Integer, String, Float, Date
from database import Base

class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    cost_per_kg = Column(Float)
    calories_per_kg = Column(Float)
    protein_per_kg = Column(Float)
    stock_kg = Column(Float)

class SavedSchedule(Base):
    __tablename__ = "saved_schedules"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String)  # Stored as YYYY-MM-DD
    students_fed = Column(Integer)
    total_cost = Column(Float)
    menu_json = Column(String)  # Stores the breakdown as a string text
