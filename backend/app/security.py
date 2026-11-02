import os
from datetime import datetime,timedelta,timezone
from jose import jwt,JWTError
from passlib.context import CryptContext
from fastapi import Depends,HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import User
pwd=CryptContext(schemes=['bcrypt'],deprecated='auto'); oauth=OAuth2PasswordBearer(tokenUrl='/api/auth/login')
SECRET=os.getenv('SECRET_KEY','dev-only-change-this-secret-before-deployment'); ALG='HS256'
def hash_password(value): return pwd.hash(value)
def verify_password(value,hashed): return pwd.verify(value,hashed)
def token_for(user): return jwt.encode({'sub':user.id,'exp':datetime.now(timezone.utc)+timedelta(minutes=int(os.getenv('JWT_EXPIRE_MINUTES','720')))},SECRET,algorithm=ALG)
def get_db():
    db=SessionLocal()
    try: yield db
    finally: db.close()
def current_user(token:str=Depends(oauth),db:Session=Depends(get_db)):
    try: uid=jwt.decode(token,SECRET,algorithms=[ALG]).get('sub')
    except JWTError: raise HTTPException(401,'Invalid or expired access token')
    user=db.get(User,uid)
    if not user: raise HTTPException(401,'Account not found')
    return user
def roles(*allowed):
    def guard(user:User=Depends(current_user)):
        if user.role not in allowed: raise HTTPException(403,'Insufficient role permissions')
        return user
    return guard
