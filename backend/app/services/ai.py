import re,math,os
from pathlib import Path
try:
 import joblib
 MODEL=joblib.load(Path(__file__).resolve().parents[2]/'ml'/'models'/'complaint_classifier.joblib')
except Exception:
 MODEL=None
CATEGORIES={
 'Roads and potholes':['pothole','road','street','crater','pavement'],
 'Garbage and sanitation':['garbage','trash','waste','rubbish','dump','sanitation'],
 'Water supply':['water','leak','pipe','supply'], 'Drainage':['drain','sewer','flood','blocked'],
 'Electricity and streetlights':['light','streetlight','electricity','wire','power'],
 'Traffic':['traffic','signal','congestion'], 'Pollution':['pollution','smoke','noise'],
 'Public infrastructure':['footpath','bridge','park','bench']}
DEPARTMENTS={'Roads and potholes':'Road Maintenance','Garbage and sanitation':'Sanitation','Water supply':'Water Supply','Drainage':'Drainage','Electricity and streetlights':'Electrical','Traffic':'Traffic','Pollution':'Environment','Public infrastructure':'Public Works'}
CRITICAL=['collapse','exposed wire','electrocution','injury','trapped','overflowing into homes','fire']
HIGH=['dangerous','major leak','blocked road','school','hospital','no water','open manhole']
def tokens(s): return set(re.findall(r'\w+',s.lower()))
def classify(text,category=None):
    t=text.lower(); scores={c:sum(w in t for w in ws) for c,ws in CATEGORIES.items()}; best=max(scores,key=scores.get)
    confidence=round(min(.98,.45+.13*scores.get(best,0)),2) if best!='Other civic problems' else .35
    method='keyword rules'
    if MODEL is not None and text.strip():
        best=str(MODEL.predict([text])[0]); probs=MODEL.predict_proba([text])[0]; confidence=round(float(max(probs)),3); method='TF-IDF + LogisticRegression trained on the bundled demo corpus'
    if category in CATEGORIES: best=category
    elif scores[best]==0: best='Other civic problems'
    return {'category':best,'confidence':confidence,'department':DEPARTMENTS.get(best,'Public Works'),'reason':f'{method}; small demonstration corpus, official should review.'}
def priority(text,category,affected=1,duplicates=0):
    t=text.lower(); level='Critical' if any(x in t for x in CRITICAL) else 'High' if any(x in t for x in HIGH) or affected>=50 else 'Medium' if category!='Other civic problems' else 'Low'
    hours={'Critical':4,'High':24,'Medium':72,'Low':168}[level]
    return {'priority':level,'sla_hours':hours,'reason':f'{level} suggestion based on safety keywords, category and reported impact ({affected} people); this is not an emergency assessment.'}
def similarity(a,b):
    x,y=tokens(a),tokens(b)
    return len(x&y)/math.sqrt(max(1,len(x)*len(y)))
def detect_duplicates(text,category,lat,lon,items):
    out=[]
    for c in items:
        score=similarity(text,c.description)
        if category==c.category: score=min(1,score+.15)
        if lat is not None and lon is not None and c.latitude is not None and c.longitude is not None:
            d=math.sqrt((lat-c.latitude)**2+(lon-c.longitude)**2); score=min(1,score+(0.3 if d<.003 else 0))
        if score>=.27: out.append({'tracking_id':c.tracking_id,'title':c.title,'similarity':round(score,2)})
    return sorted(out,key=lambda x:x['similarity'],reverse=True)[:5]
FAQ=[('track complaint','Track a complaint from the citizen complaints page with your tracking ID.','JanSetu demonstration guide; reviewed 2026-11-02.'),('birth certificate','Birth registration and certificates are handled by the relevant municipal or state civil registration authority. Please confirm documents and application steps on your local authority website.','Office of the Registrar General of India; verify current local process at https://crsorgi.gov.in/.'),('property tax','Property tax payment is managed by your municipal corporation. Use the official corporation website for your city; JanSetu does not process payments.','Relevant municipal corporation website; current city source not configured.'),('scheme','Browse the scheme directory for demonstration entries and follow each official source link to confirm current eligibility.','JanSetu demonstration guide; reviewed 2026-11-02.')]
def answer(query,language='en'):
    q=query.lower(); match=next((x for x in FAQ if x[0] in q),None)
    if not match: return {'answer':'I do not have a verified answer in the local knowledge base. Please check the relevant government department website.','source':'No matching curated source configured.','language':language}
    return {'answer':match[1],'source':match[2],'language':language}
