from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text, Boolean, func, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship, joinedload
from pydantic import BaseModel
from datetime import datetime, date
from typing import List, Optional
import os
import json
import urllib.request

load_dotenv()

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

class WeChatLogin(BaseModel):
    code: str

class DreamCreate(BaseModel):
    user_id: int
    content: str
    is_public: Optional[int] = 0
    auto_ai: Optional[bool] = True

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

# --- Combined AI Logic (DeepSeek Anthropic API Compatibility) ---
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://api.deepseek.com/anthropic")
ANTHROPIC_AUTH_TOKEN = os.getenv("ANTHROPIC_AUTH_TOKEN")
AI_ENABLED = ANTHROPIC_AUTH_TOKEN is not None and ANTHROPIC_AUTH_TOKEN != ""

def get_ai_length_constraints(raw_content: str) -> tuple:
    # 返回 (expanded_constraint, analysis_constraint)
    input_len = len(raw_content)
    if input_len < 50:
        expanded = "扩充后的字数控制在 150-200 字左右，内容简练生动"
        analysis = "解梦分析的字数控制在 100-150 字左右，简明扼要"
    elif input_len < 150:
        expanded = "扩充后的字数控制在 200-300 字左右，内容丰富且无废话"
        analysis = "解梦分析的字数控制在 150-200 字左右，提炼出关键点"
    else:
        expanded = f"由于原梦境内容较长（当前为 {input_len} 字），扩充内容需要比原梦境更具画面感且更丰富，字数控制在 {int(input_len * 1.5)} 字左右，避免臃肿"
        analysis = "解梦分析的字数控制在 200-300 字左右，深度剖析并给出明确的现实建议"
    return expanded, analysis

def process_ai_all(text: str) -> dict:
    default_res = {
        "refined": None,
        "expanded": None,
        "analysis": None
    }
    if not AI_ENABLED: 
        return default_res
    
    expanded_constraint, analysis_constraint = get_ai_length_constraints(text)
    
    prompt = f"""你是一个专业的梦境解析和内容生成助手。请对以下梦境内容进行深度处理，并返回一个符合以下要求的 JSON 字符串。

请直接返回一个符合 JSON 格式的字符串，不要包含任何 Markdown 代码块标记（如 ```json 或 ```），也不要有任何前导或后继的解释性文字。JSON 结构必须严格包含以下三个字段：
1. "refined": 对梦境内容的精炼整理。去除口语化和冗余词汇，梳理出清晰的梦境主线故事，语言凝练流畅（字数在 100 字以内，或者为原梦境的 50% 长度）。
2. "expanded": 梦境的奇幻细节扩充。展开脑洞，拒绝文艺矫情，要写得新奇有趣、脑洞大开、充满魔幻现实主义或幽默荒诞的色彩，补充有趣的感官描写（如画面、声音、氛围等），将其扩展成一段有趣的梦境短故事。要求：{expanded_constraint}。
3. "analysis": 专业的心理学解梦分析。写得非常专业、学术派，巧妙运用弗洛伊德精神分析、荣格原型理论、脑科学或一些高深词汇（如“防御机制”、“阿尼玛投射”、“集体无意识”、“边缘系统过度激活”、“镜像阶段”等），听起来非常权威、深奥且能够彻底“折服/忽悠”住普通人，并给出一句温和的现实建议。要求：{analysis_constraint}。

梦境内容：{text}"""
    
    url = f"{ANTHROPIC_BASE_URL.rstrip('/')}/v1/messages"
    headers = {
        "x-api-key": ANTHROPIC_AUTH_TOKEN,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    payload = {
        "model": "deepseek-v4-flash",
        "max_tokens": 4096,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    
    try:
        import ssl
        context = ssl._create_unverified_context()
        req = urllib.request.Request(
            url, 
            data=json.dumps(payload).encode("utf-8"), 
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req, context=context, timeout=60) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            
        content_list = res_data.get("content", [])
        raw_text = None
        for item in content_list:
            if item.get("type") == "text":
                raw_text = item.get("text", "").strip()
                break
                
        if raw_text:
            # 清理可能存在的 markdown 代码块包裹
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            elif raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()
            
            parsed = json.loads(raw_text)
            return {
                "refined": parsed.get("refined", default_res["refined"]),
                "expanded": parsed.get("expanded", default_res["expanded"]),
                "analysis": parsed.get("analysis", default_res["analysis"])
            }
    except Exception as e:
        print(f"Error calling DeepSeek Anthropic API: {e}")
        return default_res
    return default_res

def call_deepseek_single(prompt: str) -> str:
    if not AI_ENABLED:
        return "AI 功能目前未开启，请先配置 API Key"
    
    url = f"{ANTHROPIC_BASE_URL.rstrip('/')}/v1/messages"
    headers = {
        "x-api-key": ANTHROPIC_AUTH_TOKEN,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    payload = {
        "model": "deepseek-v4-flash",
        "max_tokens": 2048,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    try:
        import ssl
        context = ssl._create_unverified_context()
        req = urllib.request.Request(
            url, 
            data=json.dumps(payload).encode("utf-8"), 
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req, context=context, timeout=60) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            
        content_list = res_data.get("content", [])
        for item in content_list:
            if item.get("type") == "text":
                return item.get("text", "").strip()
    except Exception as e:
        print(f"Error calling DeepSeek API for single feature: {e}")
    return "生成失败，请稍后重试。"

def clean_placeholder(val):
    if not val: return None
    placeholders = ["AI正在精炼", "正在通过AI", "AI正在深度", "待开启", "未启用AI", "生成失败"]
    for p in placeholders:
        if p in val: return None
    return val

# --- Helpers ---
def get_dream_stats(dream, user_id, db: Session):
    d = dream.__dict__.copy()
    d['username'] = dream.user.username if dream.user else "Unknown"
    d['refined_content'] = clean_placeholder(d.get('refined_content'))
    d['expanded_content'] = clean_placeholder(d.get('expanded_content'))
    d['analysis_content'] = clean_placeholder(d.get('analysis_content'))
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

@app.post("/wechat_login", response_model=UserOut)
def wechat_login(data: WeChatLogin, db: Session = Depends(get_db)):
    # --- 微信小程序配置 ---
    # 开发提示：如果您有真实的 AppID 和 AppSecret，请在此填写
    WECHAT_APPID = "wx20c4c4720dfe451a"
    WECHAT_APPSECRET = "请在此处填写您的AppSecret"
    
    # 自动识别 Mock 模式：如果没有配置真实 Secret，则生成一个 Mock OpenID 供本地调试
    if not WECHAT_APPSECRET or "填写" in WECHAT_APPSECRET:
        openid = f"mock_user_{data.code[:8]}"
        print(f"DEBUG: Running in Mock Login mode. OpenID: {openid}")
    else:
        url = f"https://api.weixin.qq.com/sns/jscode2session?appid={WECHAT_APPID}&secret={WECHAT_APPSECRET}&js_code={data.code}&grant_type=authorization_code"
        try:
            import ssl
            context = ssl._create_unverified_context()
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, context=context) as response:
                res_data = json.loads(response.read().decode())
                
            openid = res_data.get("openid")
            if not openid:
                raise HTTPException(400, f"微信登录失败: {res_data.get('errmsg')}")
        except Exception as e:
            if isinstance(e, HTTPException): raise e
            raise HTTPException(500, f"微信接口调用异常: {str(e)}")
        
    u = db.query(User).filter(User.username == openid).first()
    if not u:
        is_admin = db.query(User).count() == 0
        u = User(username=openid, is_admin=is_admin)
        db.add(u); db.commit(); db.refresh(u)
        
    return u

@app.post("/dreams", response_model=DreamOut)
def create_dream(dream: DreamCreate, db: Session = Depends(get_db)):
    if dream.auto_ai:
        ai_res = process_ai_all(dream.content)
        refined = ai_res.get('refined')
        expanded = ai_res.get('expanded')
        analysis = ai_res.get('analysis')
    else:
        refined = None
        expanded = None
        analysis = None

    d = DreamRecord(
        user_id=dream.user_id, 
        raw_content=dream.content, 
        is_public=dream.is_public,
        refined_content=refined,
        expanded_content=expanded,
        analysis_content=analysis
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
def get_comm(page: int = 1, sort_by: str = "date", keyword: Optional[str] = None, user_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(DreamRecord).options(joinedload(DreamRecord.user)).filter(DreamRecord.is_public == 1)
    if keyword:
        q = q.filter(DreamRecord.raw_content.contains(keyword))
    if sort_by == "likes": q = q.outerjoin(Like).group_by(DreamRecord.id).order_by(func.count(Like.id).desc())
    elif sort_by == "favorites": q = q.outerjoin(Favorite).group_by(DreamRecord.id).order_by(func.count(Favorite.id).desc())
    else: q = q.order_by(DreamRecord.record_date.desc())
    dreams = q.offset((page-1)*10).limit(10).all()
    return [get_dream_stats(d, user_id, db) for d in dreams]

@app.get("/dreams/faved/{user_id}", response_model=List[DreamOut])
def get_faved_dreams(user_id: int, db: Session = Depends(get_db)):
    dreams = db.query(DreamRecord).join(Favorite).filter(Favorite.user_id == user_id).all()
    return [get_dream_stats(d, user_id, db) for d in dreams]

@app.get("/dreams/liked/{user_id}", response_model=List[DreamOut])
def get_liked_dreams(user_id: int, db: Session = Depends(get_db)):
    dreams = db.query(DreamRecord).join(Like).filter(Like.user_id == user_id).all()
    return [get_dream_stats(d, user_id, db) for d in dreams]

@app.put("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, data: dict, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == user_id).first()
    if not u: raise HTTPException(404)
    if "signature" in data: u.signature = data["signature"]
    db.commit(); db.refresh(u)
    return u

@app.get("/checkin/{user_id}")
def get_checkins(user_id: int, db: Session = Depends(get_db)):
    checks = db.query(Checkin).filter(Checkin.user_id == user_id).all()
    return [c.checkin_date for c in checks]

@app.post("/checkin")
def do_checkin(data: dict, db: Session = Depends(get_db)):
    exist = db.query(Checkin).filter(Checkin.user_id == data['user_id'], Checkin.checkin_date == data['checkin_date']).first()
    if exist: return {"success": True}
    c = Checkin(user_id=data['user_id'], checkin_date=data['checkin_date'])
    db.add(c); db.commit()
    return {"success": True}

# --- Admin Routes ---
@app.get("/admin/dreams", response_model=List[DreamOut])
def admin_list_dreams(admin_id: int, db: Session = Depends(get_db)):
    admin = db.query(User).filter(User.id == admin_id, User.is_admin == True).first()
    if not admin: raise HTTPException(403)
    dreams = db.query(DreamRecord).options(joinedload(DreamRecord.user)).order_by(DreamRecord.record_date.desc()).all()
    return [get_dream_stats(d, admin_id, db) for d in dreams]

@app.delete("/admin/dream/{dream_id}")
def admin_del_dream(dream_id: int, admin_id: int, db: Session = Depends(get_db)):
    admin = db.query(User).filter(User.id == admin_id, User.is_admin == True).first()
    if not admin: raise HTTPException(403)
    d = db.query(DreamRecord).filter(DreamRecord.id == dream_id).first()
    if d: db.delete(d); db.commit()
    return {"success": True}

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

@app.post("/dreams/{dream_id}/ai/{feature_type}", response_model=DreamOut)
def run_individual_ai(dream_id: int, feature_type: str, user_id: int, db: Session = Depends(get_db)):
    d = db.query(DreamRecord).filter(DreamRecord.id == dream_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Dream not found")
    if d.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    if feature_type not in ["refined", "expanded", "analysis"]:
        raise HTTPException(status_code=400, detail="Invalid feature type")
        
    if feature_type == "refined":
        prompt = f"""你是一个专业的梦境精炼助手。请将以下梦境内容进行精炼整理。
去除口语化和冗余词汇，梳理出清晰的梦境主线故事，语言凝练流畅（字数在 100 字以内）。
请直接返回精炼后的梦境描述文本，不要有任何解释性文字或 Markdown 标签，不要用“这是一段...”开头。

梦境内容：{d.raw_content}"""
        res = call_deepseek_single(prompt)
        d.refined_content = res
    elif feature_type == "expanded":
        expanded_constraint, _ = get_ai_length_constraints(d.raw_content)
        prompt = f"""你是一个脑洞大开的梦境细节扩充助手。请根据以下梦境内容进行奇幻细节扩充。
发挥想象力，拒绝文艺矫情，要写得新奇有趣、脑洞大开、充满魔幻现实主义或幽默荒诞的色彩，补充有趣的感官描写（如画面、声音、氛围等），将其扩展成一段具有沉浸感、奇妙有趣的梦境故事。
要求：{expanded_constraint}。
请直接返回扩充后的故事文本，不要有任何解释性文字或 Markdown 标签，不要用“这是一段...”开头。

梦境内容：{d.raw_content}"""
        res = call_deepseek_single(prompt)
        d.expanded_content = res
    elif feature_type == "analysis":
        _, analysis_constraint = get_ai_length_constraints(d.raw_content)
        prompt = f"""你是一个殿堂级的资深心理学解梦大师。请对以下梦境内容进行解梦分析。
写得必须非常专业、学术派，巧妙运用弗洛伊德精神分析、荣格原型理论、认知神经学甚至一些高深词汇（如“防御机制”、“集体无意识”、“镜像阶段”、“阿尼玛投射”、“边缘系统过度激活”等），听起来非常权威、深奥且能够折服和“忽悠”住普通人，并给出一句切实、温和的现实建议。
要求：{analysis_constraint}。
请直接返回解梦分析文本，不要有任何解释性文字或 Markdown 标签，不要用“这是一段...”开头。

梦境内容：{d.raw_content}"""
        res = call_deepseek_single(prompt)
        d.analysis_content = res
        
    db.commit()
    db.refresh(d)
    return get_dream_stats(d, user_id, db)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
