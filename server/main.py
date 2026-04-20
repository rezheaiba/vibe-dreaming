from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text, Boolean, func, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship, joinedload
from pydantic import BaseModel
from datetime import datetime, date
from typing import List, Optional
import os
import openai
import json

# --- Database Setup ---
SQLALCHEMY_DATABASE_URL = "sqlite:///../dreams.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Models ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    is_admin = Column(Boolean, default=False)
    signature = Column(String, default="这个人很懒，什么都没留下~")
    level = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    dreams = relationship("DreamRecord", back_populates="user")

class DreamRecord(Base):
    __tablename__ = "dream_records"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    record_date = Column(DateTime, default=datetime.utcnow)
    raw_content = Column(Text)
    refined_content = Column(Text, nullable=True)
    expanded_content = Column(Text, nullable=True)
    analysis_content = Column(Text, nullable=True)
    is_public = Column(Integer, default=0)
    user = relationship("User", back_populates="dreams")

class Like(Base):
    __tablename__ = "likes"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    dream_id = Column(Integer, ForeignKey("dream_records.id"))

class Favorite(Base):
    __tablename__ = "favorites"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    dream_id = Column(Integer, ForeignKey("dream_records.id"))

class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    dream_id = Column(Integer, ForeignKey("dream_records.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    parent_id = Column(Integer, ForeignKey("comments.id"), nullable=True)
    root_id = Column(Integer, ForeignKey("comments.id"), nullable=True)
    content = Column(Text)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class CommentLike(Base):
    __tablename__ = "comment_likes"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    comment_id = Column(Integer, ForeignKey("comments.id"))

class Checkin(Base):
    __tablename__ = "checkins"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    checkin_date = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# --- Pydantic Schemas ---
class UserOut(BaseModel):
    id: int
    username: str
    is_admin: bool
    signature: str
    level: int
    class Config: from_attributes = True

class DreamCreate(BaseModel):
    user_id: int
    content: str
    is_public: Optional[int] = 0

class DreamOut(BaseModel):
    id: int
    user_id: int
    record_date: datetime
    raw_content: str
    refined_content: Optional[str] = None
    expanded_content: Optional[str] = None
    analysis_content: Optional[str] = None
    is_public: Optional[int]
    username: Optional[str] = None
    like_count: int = 0
    fav_count: int = 0
    comment_count: int = 0
    is_liked: bool = False
    is_faved: bool = False
    class Config: from_attributes = True

class CommentCreate(BaseModel):
    dream_id: int
    user_id: int
    content: str
    parent_id: Optional[int] = None
    root_id: Optional[int] = None

class CommentOut(BaseModel):
    id: int
    dream_id: int
    user_id: int
    parent_id: Optional[int] = None
    root_id: Optional[int] = None
    content: str
    is_deleted: bool
    created_at: datetime
    username: Optional[str] = None
    reply_to: Optional[str] = None
    like_count: int = 0
    is_liked: bool = False
    class Config: from_attributes = True

# --- Dependency ---
def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# --- Combined AI Logic (MASSIVE SPEEDUP) ---
openai.api_key = os.getenv("OPENAI_API_KEY")
OPENAI_ENABLED = openai.api_key is not None

def process_ai_all(text: str) -> dict:
    default_res = {
        "refined": "AI正在精炼您的梦境...",
        "expanded": "正在通过AI扩充梦境细节...",
        "analysis": "AI正在深度解析您的潜意识..."
    }
    if not OPENAI_ENABLED: return default_res
    
    prompt = f"""请对以下梦境内容进行处理，并以JSON格式严格返回（不要包含Markdown代码块，仅返回JSON字符串）。
    JSON结构包含三个字段：
    1. refined: 精炼后的梦境描述
    2. expanded: 扩充后的奇幻梦境细节
    3. analysis: 心理学解梦分析
    
    梦境内容：{text}"""
    
    try:
        resp = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" }
        )
        return json.loads(resp.choices[0].message.content)
    except: return default_res

# --- Helpers ---
def get_dream_stats(dream, user_id, db: Session):
    d = dream.__dict__.copy()
    d['username'] = dream.user.username if dream.user else "Unknown"
    d['like_count'] = db.query(Like).filter(Like.dream_id == dream.id).count()
    d['fav_count'] = db.query(Favorite).filter(Favorite.dream_id == dream.id).count()
    d['comment_count'] = db.query(Comment).filter(Comment.dream_id == dream.id, Comment.is_deleted == False).count()
    if user_id:
        d['is_liked'] = db.query(Like).filter(Like.dream_id == dream.id, Like.user_id == user_id).first() is not None
        d['is_faved'] = db.query(Favorite).filter(Favorite.dream_id == dream.id, Favorite.user_id == user_id).first() is not None
    return d

# --- Routes ---
app = FastAPI(title="巡游梦境 API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.post("/users", response_model=UserOut)
def login(user: dict, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.username == user['username']).first()
    if not u:
        is_admin = db.query(User).count() == 0
        u = User(username=user['username'], is_admin=is_admin)
        db.add(u); db.commit(); db.refresh(u)
    return u

@app.post("/dreams", response_model=DreamOut)
def create_dream(dream: DreamCreate, db: Session = Depends(get_db)):
    # 1. 保存前合并 AI 调用，极大减少等待时间
    ai_res = process_ai_all(dream.content)
    d = DreamRecord(
        user_id=dream.user_id, 
        raw_content=dream.content, 
        is_public=dream.is_public,
        refined_content=ai_res.get('refined'),
        expanded_content=ai_res.get('expanded'),
        analysis_content=ai_res.get('analysis')
    )
    db.add(d); db.commit(); db.refresh(d)
    return get_dream_stats(d, dream.user_id, db)

@app.get("/dreams/detail/{dream_id}", response_model=DreamOut)
def get_dream_detail(dream_id: int, user_id: Optional[int] = None, db: Session = Depends(get_db)):
    d = db.query(DreamRecord).options(joinedload(DreamRecord.user)).filter(DreamRecord.id == dream_id).first()
    if not d: raise HTTPException(404)
    return get_dream_stats(d, user_id, db)

@app.get("/dreams/user/{user_id}", response_model=List[DreamOut])
def get_user_dreams(user_id: int, db: Session = Depends(get_db)):
    dreams = db.query(DreamRecord).options(joinedload(DreamRecord.user)).filter(DreamRecord.user_id == user_id).order_by(DreamRecord.record_date.desc()).all()
    return [get_dream_stats(d, user_id, db) for d in dreams]

@app.get("/community", response_model=List[DreamOut])
def get_comm(page: int = 1, sort_by: str = "date", user_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(DreamRecord).options(joinedload(DreamRecord.user)).filter(DreamRecord.is_public == 1)
    if sort_by == "likes": q = q.outerjoin(Like).group_by(DreamRecord.id).order_by(func.count(Like.id).desc())
    elif sort_by == "favorites": q = q.outerjoin(Favorite).group_by(DreamRecord.id).order_by(func.count(Favorite.id).desc())
    else: q = q.order_by(DreamRecord.record_date.desc())
    dreams = q.offset((page-1)*10).limit(10).all()
    return [get_dream_stats(d, user_id, db) for d in dreams]

@app.get("/comments/{dream_id}", response_model=List[CommentOut])
def list_comments(dream_id: int, user_id: Optional[int] = None, db: Session = Depends(get_db)):
    raw = db.query(Comment).filter(Comment.dream_id == dream_id).order_by(Comment.created_at.asc()).all()
    res = []
    for c in raw:
        u = db.query(User).filter(User.id == c.user_id).first()
        item = c.__dict__.copy()
        item['username'] = u.username if u else "Unknown"
        item['like_count'] = db.query(CommentLike).filter(CommentLike.comment_id == c.id).count()
        item['is_liked'] = db.query(CommentLike).filter(CommentLike.comment_id == c.id, CommentLike.user_id == user_id).first() is not None
        if c.parent_id:
            p = db.query(Comment).filter(Comment.id == c.parent_id).first()
            if p:
                pu = db.query(User).filter(User.id == p.user_id).first()
                item['reply_to'] = pu.username if pu else "Unknown"
        res.append(item)
    return res

@app.post("/comments", response_model=CommentOut)
def add_comm(c: CommentCreate, db: Session = Depends(get_db)):
    comment = Comment(dream_id=c.dream_id, user_id=c.user_id, content=c.content, parent_id=c.parent_id, root_id=c.root_id)
    db.add(comment); db.commit(); db.refresh(comment)
    u = db.query(User).filter(User.id == c.user_id).first()
    res = comment.__dict__
    res['username'] = u.username
    return res

@app.delete("/comments/{comment_id}")
def del_comm(comment_id: int, user_id: int, db: Session = Depends(get_db)):
    c = db.query(Comment).filter(Comment.id == comment_id).first()
    if not c or c.user_id != user_id: raise HTTPException(403)
    if c.parent_id is None:
        db.query(Comment).filter(Comment.root_id == c.id).delete()
        db.delete(c)
    else:
        c.is_deleted = True
        c.content = "该评论已被删除"
    db.commit()
    return {"success": True}

@app.post("/dreams/like/{dream_id}")
def like(dream_id: int, user_id: int, db: Session = Depends(get_db)):
    exist = db.query(Like).filter(Like.dream_id == dream_id, Like.user_id == user_id).first()
    if exist: db.delete(exist)
    else: db.add(Like(dream_id=dream_id, user_id=user_id))
    db.commit(); return {"success": True}

@app.post("/dreams/fav/{dream_id}")
def fav(dream_id: int, user_id: int, db: Session = Depends(get_db)):
    exist = db.query(Favorite).filter(Favorite.dream_id == dream_id, Favorite.user_id == user_id).first()
    if exist: db.delete(exist)
    else: db.add(Favorite(dream_id=dream_id, user_id=user_id))
    db.commit(); return {"success": True}

@app.post("/comments/like/{comment_id}")
def like_c(comment_id: int, user_id: int, db: Session = Depends(get_db)):
    exist = db.query(CommentLike).filter(CommentLike.comment_id == comment_id, CommentLike.user_id == user_id).first()
    if exist: db.delete(exist)
    else: db.add(CommentLike(comment_id=comment_id, user_id=user_id))
    db.commit(); return {"success": True}

@app.delete("/dreams/{dream_id}")
def del_dream(dream_id: int, user_id: int, db: Session = Depends(get_db)):
    d = db.query(DreamRecord).filter(DreamRecord.id == dream_id).first()
    if not d or d.user_id != user_id: raise HTTPException(403)
    db.delete(d); db.commit(); return {"success": True}

@app.put("/dreams/{dream_id}")
def update_dream(dream_id: int, up: dict, db: Session = Depends(get_db)):
    d = db.query(DreamRecord).filter(DreamRecord.id == dream_id).first()
    if not d or d.user_id != up['user_id']: raise HTTPException(403)
    if 'content' in up: d.raw_content = up['content']
    if 'is_public' in up: d.is_public = up['is_public']
    db.commit(); return {"success": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
