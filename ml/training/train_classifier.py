from pathlib import Path
import csv,joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import cross_val_score
from sklearn.metrics import classification_report
ROOT=Path(__file__).resolve().parents[1]
BACKEND=ROOT.parent/'backend'/'ml'
rows=list(csv.DictReader((ROOT/'datasets/complaints.csv').open(encoding='utf-8')))
X=[r['text'] for r in rows]; y=[r['category'] for r in rows]
model=Pipeline([('tfidf',TfidfVectorizer(ngram_range=(1,2),strip_accents='unicode')),('classifier',LogisticRegression(max_iter=1000,class_weight='balanced'))])
scores=cross_val_score(model,X,y,cv=3,scoring='accuracy'); model.fit(X,y)
(BACKEND/'models').mkdir(parents=True,exist_ok=True); joblib.dump(model,BACKEND/'models'/'complaint_classifier.joblib')
print('3-fold accuracy mean:',round(scores.mean(),3),'std:',round(scores.std(),3),'n=',len(y))
print(classification_report(y,model.predict(X),zero_division=0))
