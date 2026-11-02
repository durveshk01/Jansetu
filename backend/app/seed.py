from sqlalchemy import select
from .database import SessionLocal
from .models import User,Department,Complaint,StatusHistory
from .security import hash_password
from .services.ai import DEPARTMENTS,priority
from datetime import datetime,timedelta,timezone
def seed():
 db=SessionLocal()
 try:
  for name in set(DEPARTMENTS.values()):
   if not db.scalar(select(Department).where(Department.name==name)):db.add(Department(name=name,description=f'Demonstration {name} service team'))
  db.commit(); depts={d.name:d.id for d in db.scalars(select(Department)).all()}
  users=[('admin@jansetu.demo','JanSetu Administrator','government_administrator',None),('superadmin@jansetu.demo','JanSetu Super Administrator','super_administrator',None),('manager@jansetu.demo','Demo Department Manager','department_manager',next(iter(depts.values()))),('manager2@jansetu.demo','Demo Water Department Manager','department_manager',depts.get('Water Supply')),('officer@jansetu.demo','Demo Department Officer','department_officer',next(iter(depts.values())))]
  users += [(f'officer{i}@jansetu.demo',f'Demo Department Officer {i}','department_officer',list(depts.values())[i%len(depts)]) for i in range(2,6)]
  users += [('citizen@jansetu.demo','Demo Citizen','citizen',None)] + [(f'citizen{i}@jansetu.demo',f'Demo Citizen {i}','citizen',None) for i in range(2,11)]
  for email,name,role,did in users:
   if not db.scalar(select(User).where(User.email==email)):db.add(User(email=email,name=name,role=role,department_id=did,password_hash=hash_password('JanSetuDemo!2026'),city='Demo City',state='Maharashtra'))
  db.commit(); citizen=db.scalar(select(User).where(User.email=='citizen@jansetu.demo'))
  if db.scalar(select(Complaint).limit(1)) is None:
   examples=[('Large pothole on main road','A deep pothole is creating a dangerous hazard near the bus stop.','Roads and potholes',19.076,72.877),('Garbage collection missed','Waste has not been collected from the lane for three days.','Garbage and sanitation',19.08,72.88),('Streetlight not working','Streetlight has been out for a week near the park.','Electricity and streetlights',19.07,72.87),('Water pipe leaking','Water leaking onto the street from a pipe joint.','Water supply',19.09,72.89),('Blocked drain','Drain is blocked and water is collecting.','Drainage',19.075,72.88)]
   for i in range(30):
    title,desc,cat,lat,lon=examples[i%len(examples)]; pr=priority(desc,cat)
    c=Complaint(tracking_id=f'JS-DEMO{i+1:04}',citizen_id=citizen.id,title=title,description=desc,category=cat,priority=pr['priority'],priority_reason='Demonstration record; local priority rules.',status=['SUBMITTED','UNDER REVIEW','ASSIGNED','IN PROGRESS','RESOLVED'][i%5],department_id=depts.get(DEPARTMENTS.get(cat)),latitude=lat+(i%7)*.001,longitude=lon+(i%6)*.001,location_text='Demo City (fictional sample location)',created_at=datetime.now(timezone.utc)-timedelta(days=i),deadline=datetime.now(timezone.utc)+timedelta(days=3))
    db.add(c); db.flush(); db.add(StatusHistory(complaint_id=c.id,status=c.status,actor_id=citizen.id,note='Fictional seed data for demonstration.'))
   db.commit()
 finally:db.close()
