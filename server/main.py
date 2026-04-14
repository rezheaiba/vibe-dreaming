from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

# --- Database Setup ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./dreams.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Models ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class DreamRecord(Base):
    __tablename__ = "dream_records"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    record_date = Column(DateTime, default=datetime.utcnow)
    raw_content = Column(Text)
    refined_content = Column(Text, nullable=True)
    expanded_content = Column(Text, nullable=True)
    status = Column(String, default="pending")  # pending/processing/completed

# Create tables
Base.metadata.create_all(bind=engine)

# --- AI Placeholder Functions ---
def process_refine(text: str) -> str:
    """
    Placeholder for AI refinement logic.
    Integrate with an LLM here in the future.
    """
    return f"Refined: {text[:20]}..."

def process_expand(text: str) -> str:
    """
    Placeholder for AI expansion logic.
    Integrate with an LLM here in the future.
    """
    return f"Expanded: Once upon a dream, someone wrote: {text}"

# --- Pydantic Schemas ---
class DreamCreate(BaseModel):
    user_id: int
    content: str

class DreamOut(BaseModel):
    id: int
    user_id: int
    record_date: datetime
    raw_content: str
    refined_content: Optional[str]
    expanded_content: Optional[str]
    status: str

    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    username: str

class UserOut(BaseModel):
    id: int
    username: str
    created_at: datetime

    class Config:
        from_attributes = True

# --- FastAPI App ---
app = FastAPI(title="巡游梦境 (Cruising Dreams) API")

# Enable CORS for frontend interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/users", response_model=UserOut)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        return db_user
    new_user = User(username=user.username)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/dreams", response_model=DreamOut)
def create_dream(dream: DreamCreate, db: Session = Depends(get_db)):
    # Verify user exists
    user = db.query(User).filter(User.id == dream.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Create record
    new_record = DreamRecord(
        user_id=dream.user_id,
        raw_content=dream.content,
        refined_content=process_refine(dream.content),
        expanded_content=process_expand(dream.content),
        status="completed" # Setting to completed for this demo
    )
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    return new_record

@app.get("/dreams/{user_id}", response_model=List[DreamOut])
def get_dreams(user_id: int, db: Session = Depends(get_db)):
    return db.query(DreamRecord).filter(DreamRecord.user_id == user_id).order_by(DreamRecord.record_date.desc()).all()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
