import os, json, secrets, hashlib
from datetime import datetime, timezone
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
import psycopg

DATABASE_URL=os.environ["DATABASE_URL"]
app=FastAPI(title="RichFrog Sync API", version="1.0.0")

def db():
    return psycopg.connect(DATABASE_URL)

@app.on_event("startup")
def init():
    with db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS rf_profiles(
          telegram_id BIGINT PRIMARY KEY,
          token_hash TEXT NOT NULL,
          payload JSONB NOT NULL DEFAULT '{}'::jsonb,
          public BOOLEAN NOT NULL DEFAULT TRUE,
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )""")

class Register(BaseModel):
    telegram_id: int = Field(gt=0)
class Profile(BaseModel):
    payload: dict
    public: bool = True

def auth(telegram_id, authorization):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401,"Missing device token")
    token=authorization[7:].strip()
    with db() as c:
        row=c.execute("SELECT token_hash FROM rf_profiles WHERE telegram_id=%s",(telegram_id,)).fetchone()
    if not row or not secrets.compare_digest(row[0],hashlib.sha256(token.encode()).hexdigest()):
        raise HTTPException(403,"Invalid device token")

@app.get("/")
def health():
    return {"service":"RichFrog Sync","status":"ok","identity_verified":False}

@app.post("/v1/register")
def register(body:Register):
    token=secrets.token_urlsafe(32)
    digest=hashlib.sha256(token.encode()).hexdigest()
    with db() as c:
        c.execute("""INSERT INTO rf_profiles(telegram_id,token_hash,payload,public)
          VALUES(%s,%s,'{}'::jsonb,FALSE)
          ON CONFLICT(telegram_id) DO NOTHING""",(body.telegram_id,digest))
        row=c.execute("SELECT token_hash FROM rf_profiles WHERE telegram_id=%s",(body.telegram_id,)).fetchone()
    if not secrets.compare_digest(row[0],digest):
        raise HTTPException(409,"This ID is already registered. Reinstall or recover the existing device token.")
    return {"telegram_id":body.telegram_id,"device_token":token,"identity_verified":False}

@app.put("/v1/profile/{telegram_id}")
def publish(telegram_id:int, body:Profile, authorization:str=Header(default="")):
    auth(telegram_id,authorization)
    allowed={"rating","gifts","username_labels","virtual_number_labels","worn_label"}
    clean={k:v for k,v in body.payload.items() if k in allowed}
    encoded=json.dumps(clean,ensure_ascii=False)
    if len(encoded)>16000: raise HTTPException(413,"Profile too large")
    with db() as c:
        c.execute("UPDATE rf_profiles SET payload=%s::jsonb,public=%s,updated_at=now() WHERE telegram_id=%s",(encoded,body.public,telegram_id))
    return {"ok":True,"updated_at":datetime.now(timezone.utc).isoformat()}

@app.get("/v1/profile/{telegram_id}")
def get_profile(telegram_id:int):
    with db() as c:
        row=c.execute("SELECT payload,public,updated_at FROM rf_profiles WHERE telegram_id=%s",(telegram_id,)).fetchone()
    if not row or not row[1]: raise HTTPException(404,"Profile not shared")
    return {"telegram_id":telegram_id,"payload":row[0],"public":True,"identity_verified":False,"updated_at":row[2].isoformat()}

@app.delete("/v1/profile/{telegram_id}")
def delete_profile(telegram_id:int, authorization:str=Header(default="")):
    auth(telegram_id,authorization)
    with db() as c:
        c.execute("UPDATE rf_profiles SET payload='{}'::jsonb,public=FALSE,updated_at=now() WHERE telegram_id=%s",(telegram_id,))
    return {"ok":True}
