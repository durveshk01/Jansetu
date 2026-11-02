from fastapi import FastAPI,Depends,HTTPException,UploadFile,File,Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import select,func
from pydantic import BaseModel,Field,EmailStr
from datetime import datetime,timedelta,timezone
import hashlib,uuid,os,csv,io,secrets
from pathlib import Path
from .database import init_db
from .models import User,Department,Complaint,StatusHistory,Notification,Attachment,AuditRecord
from .security import get_db,current_user,roles,hash_password,verify_password,token_for
from .services.ai import classify,priority,detect_duplicates,answer,DEPARTMENTS
app=FastAPI(title='JanSetu API',version='1.0.0',description='Local-first citizen services and transparent smart governance demo')
origins=os.getenv('CORS_ORIGINS','http://localhost:3000').split(',')
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
@app.on_event('startup')
def startup():
    init_db()
    from .seed import seed
    seed()
@app.get('/health')
def health(): return {'status':'ok','service':'jansetu-api'}
class Register(BaseModel): name:str=Field(min_length=2,max_length=120); email:EmailStr; password:str=Field(min_length=10); phone:str=''; city:str=''; state:str=''; language:str='en'
class Login(BaseModel): email:EmailStr; password:str
class ComplaintIn(BaseModel): title:str=Field(min_length=5,max_length=180); description:str=Field(min_length=10,max_length=10000); category:str='Other civic problems'; latitude:float|None=None; longitude:float|None=None; location_text:str=''; affected_people:int=Field(default=1,ge=1,le=100000)
class StatusIn(BaseModel): status:str; note:str=''
class AssignIn(BaseModel): department_id:str|None=None; officer_id:str|None=None; note:str=''
class FeedbackIn(BaseModel): rating:int=Field(ge=1,le=5); comment:str=''
def serialize(c,db):
 d=db.get(Department,c.department_id) if c.department_id else None
 return {'id':c.id,'tracking_id':c.tracking_id,'title':c.title,'description':c.description,'category':c.category,'priority':c.priority,'priority_reason':c.priority_reason,'status':c.status,'department':d.name if d else None,'department_id':c.department_id,'latitude':c.latitude,'longitude':c.longitude,'location_text':c.location_text,'created_at':c.created_at.isoformat(),'deadline':c.deadline.isoformat() if c.deadline else None,'timeline':[{'status':h.status,'note':h.note,'created_at':h.created_at.isoformat()} for h in c.histories]}
def owned(c,user):
 if user.role=='citizen' and c.citizen_id!=user.id: raise HTTPException(404,'Complaint not found')
 if user.role in ('department_officer','department_manager') and c.department_id!=user.department_id: raise HTTPException(403,'Complaint is outside your department')
@app.post('/api/auth/register')
def register(data:Register,db:Session=Depends(get_db)):
 if db.scalar(select(User).where(User.email==data.email.lower())): raise HTTPException(409,'Email is already registered')
 u=User(name=data.name,email=data.email.lower(),password_hash=hash_password(data.password),phone=data.phone,city=data.city,state=data.state,language=data.language,role='citizen'); db.add(u); db.commit(); db.refresh(u)
 return {'access_token':token_for(u),'token_type':'bearer','user':{'id':u.id,'name':u.name,'email':u.email,'role':u.role}}
@app.post('/api/auth/login')
def login(data:Login,db:Session=Depends(get_db)):
 u=db.scalar(select(User).where(User.email==data.email.lower()))
 if not u or not verify_password(data.password,u.password_hash): raise HTTPException(401,'Incorrect email or password')
 return {'access_token':token_for(u),'token_type':'bearer','user':{'id':u.id,'name':u.name,'email':u.email,'role':u.role,'department_id':u.department_id}}
@app.post('/api/auth/logout')
def logout(user:User=Depends(current_user)): return {'ok':True,'message':'Remove the bearer token from this browser.'}
@app.get('/api/auth/me')
def me(user:User=Depends(current_user)): return {'id':user.id,'name':user.name,'email':user.email,'role':user.role,'city':user.city,'state':user.state,'language':user.language,'department_id':user.department_id}
@app.get('/api/citizens/profile')
def profile(user:User=Depends(current_user)): return me(user)
@app.patch('/api/citizens/profile')
def update_profile(data:dict,user:User=Depends(current_user),db:Session=Depends(get_db)):
 for k in ('name','phone','city','state','language'):
  if k in data: setattr(user,k,str(data[k])[:120])
 db.commit(); return me(user)
@app.post('/api/ai/classify-complaint')
def ai_classify(data:dict,user:User=Depends(current_user)):
 c=classify(data.get('description',''),data.get('category')); p=priority(data.get('description',''),c['category'],int(data.get('affected_people',1))); return {**c,**p}
@app.post('/api/ai/detect-duplicates')
def ai_duplicates(data:dict,user:User=Depends(current_user),db:Session=Depends(get_db)):
 items=db.scalars(select(Complaint).where(Complaint.status!='CLOSED').limit(250)).all(); return {'possible_duplicates':detect_duplicates(data.get('description',''),data.get('category',''),data.get('latitude'),data.get('longitude'),items)}
@app.post('/api/ai/assistant')
def assistant(data:dict): return answer(data.get('query',''),data.get('language','en'))
@app.post('/api/ai/translate')
def translate(data:dict): return {'text':data.get('text',''),'language':data.get('target_language','en'),'translated':False,'notice':'Translation service is not configured; original text returned.'}
@app.post('/api/ai/analyze-image')
async def image_analysis(file:UploadFile=File(...),user:User=Depends(current_user)):
 if file.content_type not in ('image/jpeg','image/png','image/webp'): raise HTTPException(415,'Upload a JPEG, PNG, or WebP image')
 raw=await file.read(10*1024*1024+1)
 if len(raw)>10*1024*1024: raise HTTPException(413,'Image exceeds 10 MB')
 import cv2,numpy as np
 image=cv2.imdecode(np.frombuffer(raw,dtype=np.uint8),cv2.IMREAD_COLOR)
 if image is None: raise HTTPException(422,'Image could not be decoded')
 gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY); edges=cv2.Canny(gray,70,150); dark_fraction=float(np.mean(gray<65)); edge_density=float(np.mean(edges>0))
 # Explainable image cues only; not a trained pothole classifier or a safety determination.
 rough_surface=dark_fraction>.18 and edge_density>.06
 return {'filename':file.filename,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'image_features':{'width':int(image.shape[1]),'height':int(image.shape[0]),'dark_pixel_fraction':round(dark_fraction,3),'edge_density':round(edge_density,3)},'suggestion':'Possible damaged-road visual cues; human review required.' if rough_surface else 'No strong damaged-road cues from the simple visual heuristic; human review required.','model':'OpenCV grayscale, dark-region and Canny-edge heuristic; not a trained vision model.'}
@app.post('/api/complaints')
def create_complaint(data:ComplaintIn,user:User=Depends(roles('citizen')),db:Session=Depends(get_db)):
 ai=classify(data.description,data.category); pr=priority(data.description,ai['category'],data.affected_people)
 dept=db.scalar(select(Department).where(Department.name==ai['department']))
 c=Complaint(tracking_id='JS-'+secrets.token_hex(5).upper(),citizen_id=user.id,title=data.title,description=data.description,category=ai['category'],priority=pr['priority'],priority_reason=pr['reason'],status='SUBMITTED',department_id=dept.id if dept else None,latitude=data.latitude,longitude=data.longitude,location_text=data.location_text,affected_people=data.affected_people,deadline=datetime.now(timezone.utc)+timedelta(hours=pr['sla_hours']))
 db.add(c); db.flush(); db.add(StatusHistory(complaint_id=c.id,status='SUBMITTED',actor_id=user.id,note='Complaint received; AI classification and priority are suggestions for official review.'))
 db.add(Notification(user_id=user.id,title='Complaint submitted',message=f'{c.tracking_id} has been registered.')); ev=AuditRecord(complaint_id=c.id,event_type='COMPLAINT_REGISTERED',event_hash=hashlib.sha256(f'{c.id}:SUBMITTED:{c.created_at}'.encode()).hexdigest(),status='PENDING'); db.add(ev); db.commit(); db.refresh(c); return serialize(c,db)
@app.get('/api/complaints')
def complaints(status:str|None=None,category:str|None=None,search:str|None=None,limit:int=Query(50,ge=1,le=200),offset:int=Query(0,ge=0),user:User=Depends(current_user),db:Session=Depends(get_db)):
 q=select(Complaint).order_by(Complaint.created_at.desc())
 if user.role=='citizen': q=q.where(Complaint.citizen_id==user.id)
 if user.department_id and user.role in ('department_officer','department_manager'): q=q.where(Complaint.department_id==user.department_id)
 if status:q=q.where(Complaint.status==status)
 if category:q=q.where(Complaint.category==category)
 if search:q=q.where(Complaint.tracking_id.ilike(f'%{search}%'))
 return {'items':[serialize(c,db) for c in db.scalars(q.offset(offset).limit(limit)).all()],'limit':limit,'offset':offset}
@app.get('/api/complaints/{cid}')
def complaint_detail(cid:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
 c=db.get(Complaint,cid) or db.scalar(select(Complaint).where(Complaint.tracking_id==cid))
 if not c: raise HTTPException(404,'Complaint not found')
 owned(c,user); return serialize(c,db)
@app.post('/api/complaints/{cid}/update-status')
def update_status(cid:str,data:StatusIn,user:User=Depends(roles('department_officer','department_manager','government_administrator','super_administrator')),db:Session=Depends(get_db)):
 allowed={'SUBMITTED','UNDER REVIEW','VERIFIED','ASSIGNED','IN PROGRESS','RESOLVED','CLOSED','REJECTED','REOPENED'}; c=db.get(Complaint,cid)
 if not c: raise HTTPException(404,'Complaint not found')
 owned(c,user)
 if data.status not in allowed: raise HTTPException(422,'Unknown complaint status')
 c.status=data.status; db.add(StatusHistory(complaint_id=c.id,status=data.status,actor_id=user.id,note=data.note)); db.add(Notification(user_id=c.citizen_id,title='Complaint status updated',message=f'{c.tracking_id}: {data.status}'))
 db.add(AuditRecord(complaint_id=c.id,event_type='STATUS_'+data.status,event_hash=hashlib.sha256(f'{c.id}:{data.status}:{datetime.now(timezone.utc).isoformat()}'.encode()).hexdigest(),status='PENDING')); db.commit(); return serialize(c,db)
@app.post('/api/admin/complaints/{cid}/assign')
def assign(cid:str,data:AssignIn,user:User=Depends(roles('department_manager','government_administrator','super_administrator')),db:Session=Depends(get_db)):
 c=db.get(Complaint,cid)
 if not c: raise HTTPException(404,'Complaint not found')
 if data.department_id and not db.get(Department,data.department_id): raise HTTPException(404,'Department not found')
 c.department_id=data.department_id or c.department_id; c.status='ASSIGNED'; db.add(StatusHistory(complaint_id=c.id,status='ASSIGNED',actor_id=user.id,note=data.note or 'Assigned by authorized official')); db.commit(); return serialize(c,db)
@app.post('/api/complaints/{cid}/reopen')
def reopen(cid:str,data:dict,user:User=Depends(roles('citizen')),db:Session=Depends(get_db)):
 c=db.get(Complaint,cid)
 if not c or c.citizen_id!=user.id: raise HTTPException(404,'Complaint not found')
 if c.status not in ('RESOLVED','CLOSED'): raise HTTPException(409,'Only resolved complaints can be reopened')
 c.status='REOPENED'; db.add(StatusHistory(complaint_id=c.id,status='REOPENED',actor_id=user.id,note=str(data.get('reason','')))); db.commit(); return serialize(c,db)
@app.post('/api/complaints/{cid}/feedback')
def feedback(cid:str,data:FeedbackIn,user:User=Depends(roles('citizen')),db:Session=Depends(get_db)):
 c=db.get(Complaint,cid)
 if not c or c.citizen_id!=user.id: raise HTTPException(404,'Complaint not found')
 if c.status not in ('RESOLVED','CLOSED'): raise HTTPException(409,'Feedback is available after resolution')
 db.add(Notification(user_id=c.citizen_id,title='Feedback received',message=f'Thank you for rating {c.tracking_id}: {data.rating}/5.')); db.commit(); return {'saved':True,'note':'Feedback demo record acknowledged.'}
@app.post('/api/complaints/{cid}/attachments')
async def upload(cid:str,file:UploadFile=File(...),user:User=Depends(current_user),db:Session=Depends(get_db)):
 c=db.get(Complaint,cid)
 if not c: raise HTTPException(404,'Complaint not found')
 owned(c,user)
 if file.content_type not in ('image/jpeg','image/png','image/webp','application/pdf','audio/webm','audio/wav'): raise HTTPException(415,'Unsupported attachment type')
 raw=await file.read(int(os.getenv('MAX_UPLOAD_MB','10'))*1024*1024+1)
 if len(raw)>int(os.getenv('MAX_UPLOAD_MB','10'))*1024*1024: raise HTTPException(413,'Attachment exceeds configured size limit')
 folder=Path(os.getenv('UPLOAD_DIR','./private_uploads')); folder.mkdir(parents=True,exist_ok=True); fid=str(uuid.uuid4()); path=folder/fid; path.write_bytes(raw)
 db.add(Attachment(id=fid,complaint_id=c.id,filename=Path(file.filename or 'upload').name,content_type=file.content_type,path=str(path))); db.commit(); return {'id':fid,'filename':Path(file.filename or '').name,'bytes':len(raw),'private':True}
@app.get('/api/departments')
def departments(db:Session=Depends(get_db)): return [{'id':d.id,'name':d.name,'description':d.description} for d in db.scalars(select(Department).order_by(Department.name)).all()]
@app.get('/api/schemes')
def schemes(state:str|None=None,category:str|None=None):
 data=[{'id':'demo-edu','name':'Demonstration Education Support','category':'Education','description':'Fictional sample record for demonstrating scheme discovery. Not a government benefit.','eligibility':'Demo eligibility: student status selected.','benefits':'Example information only','documents':['Identity proof (example only)'],'url':'','source':'JanSetu fictional demonstration dataset','verified':False,'last_verified':'2026-11-02'}, {'id':'demo-farm','name':'Demonstration Farmer Support','category':'Agriculture','description':'Fictional sample record; does not represent a real scheme.','eligibility':'Demo eligibility: occupation farmer selected.','benefits':'Example information only','documents':['Land record (example only)'],'url':'','source':'JanSetu fictional demonstration dataset','verified':False,'last_verified':'2026-11-02'}]
 return [x for x in data if not category or x['category'].lower()==category.lower()]
@app.post('/api/schemes/check-eligibility')
def eligibility(data:dict): return {'possible_match':bool(data.get('occupation') or data.get('student')),'disclaimer':'Demonstration rule only. This does not establish entitlement; verify directly with the responsible authority.','matches':['demo-edu'] if data.get('student') else ['demo-farm'] if data.get('occupation') else []}
@app.get('/api/gis/complaints')
def gis(category:str|None=None,priority_filter:str|None=Query(None,alias='priority'),status:str|None=None,user:User=Depends(current_user),db:Session=Depends(get_db)):
 q=select(Complaint).where(Complaint.latitude.is_not(None),Complaint.longitude.is_not(None))
 if user.role=='citizen':q=q.where(Complaint.citizen_id==user.id)
 if user.department_id and user.role in ('department_officer','department_manager'):q=q.where(Complaint.department_id==user.department_id)
 if category:q=q.where(Complaint.category==category)
 if priority_filter:q=q.where(Complaint.priority==priority_filter)
 if status:q=q.where(Complaint.status==status)
 return {'type':'FeatureCollection','features':[{'type':'Feature','geometry':{'type':'Point','coordinates':[c.longitude,c.latitude]},'properties':{'id':c.id,'tracking_id':c.tracking_id,'title':c.title,'category':c.category,'priority':c.priority,'status':c.status}} for c in db.scalars(q).all()]}
@app.get('/api/gis/heatmap')
def heatmap(db:Session=Depends(get_db)): return [{'category':c,'count':n} for c,n in db.execute(select(Complaint.category,func.count()).group_by(Complaint.category)).all()]
@app.get('/api/admin/dashboard')
def admin_dashboard(user:User=Depends(roles('department_officer','department_manager','government_administrator','super_administrator')),db:Session=Depends(get_db)):
 q=select(Complaint)
 if user.department_id and user.role in ('department_officer','department_manager'):q=q.where(Complaint.department_id==user.department_id)
 allc=db.scalars(q).all(); return {'total':len(allc),'pending':sum(c.status not in ('RESOLVED','CLOSED') for c in allc),'resolved':sum(c.status in ('RESOLVED','CLOSED') for c in allc),'overdue':sum(c.deadline and c.deadline<datetime.now(timezone.utc) and c.status not in ('RESOLVED','CLOSED') for c in allc),'by_category':{x:sum(c.category==x for c in allc) for x in set(c.category for c in allc)}}
@app.get('/api/notifications')
def notifications(user:User=Depends(current_user),db:Session=Depends(get_db)): return [{'id':n.id,'title':n.title,'message':n.message,'read':n.read,'created_at':n.created_at.isoformat()} for n in db.scalars(select(Notification).where(Notification.user_id==user.id).order_by(Notification.created_at.desc())).all()]
@app.patch('/api/notifications/{nid}/read')
def read_notification(nid:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
 n=db.get(Notification,nid)
 if not n or n.user_id!=user.id: raise HTTPException(404,'Notification not found')
 n.read=True; db.commit(); return {'read':True}
@app.get('/api/blockchain/records/{cid}')
def audit_records(cid:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
 c=db.get(Complaint,cid)
 if not c:raise HTTPException(404,'Complaint not found')
 owned(c,user); return [{'id':r.id,'event_type':r.event_type,'event_hash':r.event_hash,'tx_hash':r.tx_hash,'status':r.status,'created_at':r.created_at.isoformat()} for r in db.scalars(select(AuditRecord).where(AuditRecord.complaint_id==cid)).all()]
@app.get('/api/blockchain/verify/{rid}')
def verify_audit(rid:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
 r=db.get(AuditRecord,rid)
 if not r:raise HTTPException(404,'Audit record not found')
 owned(db.get(Complaint,r.complaint_id),user)
 return {'record_id':r.id,'verification':'PENDING' if r.status=='PENDING' else 'VERIFIED' if r.status=='CONFIRMED' else 'NOT VERIFIED','tx_hash':r.tx_hash,'event_hash':r.event_hash,'message':'No configured chain transaction; database audit entry alone is not blockchain verification.' if r.status!='CONFIRMED' else 'Chain transaction confirmation recorded.'}
@app.get('/api/reports/complaints')
def report(user:User=Depends(roles('department_manager','government_administrator','super_administrator')),db:Session=Depends(get_db)):
 allc=db.scalars(select(Complaint)).all(); return {'total':len(allc),'status_counts':{s:sum(c.status==s for c in allc) for s in {c.status for c in allc}},'priority_counts':{s:sum(c.priority==s for c in allc) for s in {c.priority for c in allc}}}
@app.get('/api/reports/export')
def export(user:User=Depends(roles('department_manager','government_administrator','super_administrator')),db:Session=Depends(get_db)):
 out=io.StringIO(); w=csv.writer(out); w.writerow(['Tracking ID','Title','Category','Priority','Status','Created']);
 for c in db.scalars(select(Complaint)):w.writerow([c.tracking_id,c.title,c.category,c.priority,c.status,c.created_at.isoformat()])
 return StreamingResponse(iter([out.getvalue()]),media_type='text/csv',headers={'Content-Disposition':'attachment; filename=jansetu-complaints.csv'})
