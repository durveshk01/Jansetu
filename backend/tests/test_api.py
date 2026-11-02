import os
os.environ['SEED_DEMO_DATA']='true'
from fastapi.testclient import TestClient
import pytest
from app.main import app
@pytest.fixture(scope='module')
def client():
    with TestClient(app) as c: yield c
def token(client,email='citizen@jansetu.demo',password='JanSetuDemo!2026'):
 r=client.post('/api/auth/login',json={'email':email,'password':password}); assert r.status_code==200; return r.json()['access_token']
def test_health(client): assert client.get('/health').json()['status']=='ok'
def test_auth_and_user_isolation(client):
 t=token(client); assert client.get('/api/auth/me',headers={'Authorization':f'Bearer {t}'}).status_code==200
 items=client.get('/api/complaints',headers={'Authorization':f'Bearer {t}'}).json()['items']; assert items
 assert sum(x['tracking_id'].startswith('JS-DEMO') for x in items)>=30
def test_complaint_create_and_ai(client):
 t=token(client); h={'Authorization':f'Bearer {t}'}
 c=client.post('/api/complaints',headers=h,json={'title':'Pothole outside community hall','description':'Deep pothole in the road is dangerous to cyclists.','category':'Roads and potholes'}); assert c.status_code==200, c.text
 assert c.json()['priority'] in ('High','Critical','Medium','Low')
 assert client.get('/api/complaints/'+c.json()['id'],headers=h).status_code==200
def test_role_permissions(client):
 t=token(client); r=client.get('/api/admin/dashboard',headers={'Authorization':f'Bearer {t}'}); assert r.status_code==403
def test_assistant_and_schemes(client):
 assert client.post('/api/ai/assistant',json={'query':'How do I track complaint?'}).json()['source']
 assert client.get('/api/schemes').json()[0]['verified'] is False
