from datetime import datetime, timezone
from sqlalchemy import String, Text, Float, DateTime, ForeignKey, Integer, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import uuid

def now(): return datetime.now(timezone.utc)
class Base(DeclarativeBase): pass
class User(Base):
    __tablename__='users'
    id: Mapped[str]=mapped_column(String,primary_key=True,default=lambda:str(uuid.uuid4()))
    name: Mapped[str]=mapped_column(String(120)); email: Mapped[str]=mapped_column(String(255),unique=True,index=True)
    phone: Mapped[str]=mapped_column(String(30),default=''); city: Mapped[str]=mapped_column(String(100),default='')
    state: Mapped[str]=mapped_column(String(100),default=''); language: Mapped[str]=mapped_column(String(20),default='en')
    password_hash: Mapped[str]=mapped_column(String(255)); role: Mapped[str]=mapped_column(String(40),default='citizen',index=True)
    department_id: Mapped[str|None]=mapped_column(ForeignKey('departments.id'),nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Department(Base):
    __tablename__='departments'
    id: Mapped[str]=mapped_column(String,primary_key=True,default=lambda:str(uuid.uuid4()))
    name: Mapped[str]=mapped_column(String(120),unique=True); description: Mapped[str]=mapped_column(Text,default='')
class Complaint(Base):
    __tablename__='complaints'
    id: Mapped[str]=mapped_column(String,primary_key=True,default=lambda:str(uuid.uuid4()))
    tracking_id: Mapped[str]=mapped_column(String(24),unique=True,index=True)
    citizen_id: Mapped[str]=mapped_column(ForeignKey('users.id'),index=True)
    title: Mapped[str]=mapped_column(String(180)); description: Mapped[str]=mapped_column(Text)
    category: Mapped[str]=mapped_column(String(80),index=True); priority: Mapped[str]=mapped_column(String(20),default='Medium')
    priority_reason: Mapped[str]=mapped_column(Text,default=''); status: Mapped[str]=mapped_column(String(40),default='SUBMITTED',index=True)
    department_id: Mapped[str|None]=mapped_column(ForeignKey('departments.id'),nullable=True)
    latitude: Mapped[float|None]=mapped_column(Float,nullable=True); longitude: Mapped[float|None]=mapped_column(Float,nullable=True)
    location_text: Mapped[str]=mapped_column(String(255),default=''); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    deadline: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True); affected_people: Mapped[int]=mapped_column(Integer,default=1)
    histories: Mapped[list['StatusHistory']]=relationship(cascade='all, delete-orphan',order_by='StatusHistory.created_at')
class StatusHistory(Base):
    __tablename__='complaint_status_history'
    id: Mapped[str]=mapped_column(String,primary_key=True,default=lambda:str(uuid.uuid4()))
    complaint_id: Mapped[str]=mapped_column(ForeignKey('complaints.id'),index=True); status: Mapped[str]=mapped_column(String(40))
    actor_id: Mapped[str]=mapped_column(ForeignKey('users.id')); note: Mapped[str]=mapped_column(Text,default=''); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Attachment(Base):
    __tablename__='complaint_attachments'
    id: Mapped[str]=mapped_column(String,primary_key=True,default=lambda:str(uuid.uuid4())); complaint_id: Mapped[str]=mapped_column(ForeignKey('complaints.id'),index=True)
    filename: Mapped[str]=mapped_column(String(255)); path: Mapped[str]=mapped_column(String(512)); content_type: Mapped[str]=mapped_column(String(100)); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Notification(Base):
    __tablename__='notifications'
    id: Mapped[str]=mapped_column(String,primary_key=True,default=lambda:str(uuid.uuid4())); user_id: Mapped[str]=mapped_column(ForeignKey('users.id'),index=True)
    title: Mapped[str]=mapped_column(String(180)); message: Mapped[str]=mapped_column(Text); read: Mapped[bool]=mapped_column(Boolean,default=False)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class AuditRecord(Base):
    __tablename__='blockchain_audit_records'
    id: Mapped[str]=mapped_column(String,primary_key=True,default=lambda:str(uuid.uuid4())); complaint_id: Mapped[str]=mapped_column(ForeignKey('complaints.id'),index=True)
    event_type: Mapped[str]=mapped_column(String(80)); event_hash: Mapped[str]=mapped_column(String(64)); tx_hash: Mapped[str|None]=mapped_column(String(100),nullable=True)
    status: Mapped[str]=mapped_column(String(30),default='PENDING'); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
