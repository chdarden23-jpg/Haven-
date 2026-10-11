"""ANEIRA V3 unified FastAPI application. No rejected legacy application imports."""
import os, json, time, secrets, smtplib
from email.message import EmailMessage
from pathlib import Path
from fastapi import FastAPI,HTTPException,Request,Response,Depends
from fastapi.responses import FileResponse,JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from typing import Any
import storage, intelligence as intel
from aneira_assessment.engine import QUESTIONS, DOMAINS, validate_answers, visible_questions, longitudinal
ROOT=Path(__file__).parent
app=FastAPI(title='ANEIRA V3 | The Human Restoration Project',docs_url=None,redoc_url=None)
app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')
@app.on_event('startup')
def startup():storage.init()
@app.middleware('http')
async def protections(request,call_next):
 if os.environ.get('ANEIRA_DEMO_MODE')=='1' and request.method in ('POST','PUT','PATCH','DELETE') and request.url.path not in ('/api/logout',):
  return JSONResponse({'detail':'Demo mode does not persist sensitive information'},status_code=403)
 response=await call_next(request)
 response.headers['Cache-Control']='no-store' if request.url.path.startswith('/api') else 'no-cache'
 response.headers['X-Content-Type-Options']='nosniff';response.headers['Referrer-Policy']='no-referrer';response.headers['X-Frame-Options']='DENY'
 response.headers['Content-Security-Policy']="default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; font-src 'self'; frame-ancestors 'none'"
 return response
@app.get('/')
def home():return FileResponse(ROOT/'static/index.html')
@app.get('/health')
def health():return {'status':'ok','version':'V3','exercises':len(intel.EXERCISES),'journals':len(intel.JOURNALS),'chapters':len(intel.CHAPTERS),'questions':len(QUESTIONS)}
def uid(request:Request):
 u=storage.identify(request.cookies.get('aneira_session'))
 if u is None:raise HTTPException(401,'Sign in to access your private records')
 return u

def require_origin(request):
 origin=request.headers.get('origin');host=request.headers.get('host')
 if origin and host and not origin.endswith('://'+host):raise HTTPException(403,'Invalid request origin')

class Auth(BaseModel):email:str;password:str
class EmailOnly(BaseModel):email:str
class Reset(BaseModel):token:str;password:str
class AnswerPayload(BaseModel):answers:dict=Field(default_factory=dict);save:bool=False
class AnswerStore(AnswerPayload):name:str='current';consent:bool=False
class Progress(BaseModel):item_id:str;kind:str;completed:bool=True;helpfulness:int|None=None;note:str|None=None;consent:bool=True
class Entry(BaseModel):journal_id:str;entry_id:str;answers:dict=Field(default_factory=dict);consent:bool=False
class Cognitive(BaseModel):scenario_id:str;choice_id:str;save:bool=False
class Affirmation(BaseModel):affirmation_id:str;selection:str;reflection:str='';save:bool=False
@app.post('/api/register')
def register(p:Auth,request:Request,response:Response):
 require_origin(request)
 if not 3<=len(p.email)<=254 or '@' not in p.email:raise HTTPException(422,'Enter a valid email')
 try:storage.register(p.email,p.password);token=storage.login(p.email,p.password)
 except ValueError as ex:raise HTTPException(400,str(ex))
 response.set_cookie('aneira_session',token,httponly=True,secure=os.environ.get('ANEIRA_INSECURE_LOCAL')!='1',samesite='strict',max_age=storage.SESSION_AGE,path='/')
 return {'authenticated':True}
@app.post('/api/login')
def login(p:Auth,request:Request,response:Response):
 require_origin(request)
 try:token=storage.login(p.email,p.password)
 except ValueError:raise HTTPException(401,'Incorrect credentials')
 response.set_cookie('aneira_session',token,httponly=True,secure=os.environ.get('ANEIRA_INSECURE_LOCAL')!='1',samesite='strict',max_age=storage.SESSION_AGE,path='/');return {'authenticated':True}
@app.post('/api/logout')
def logout(request:Request,response:Response):
 require_origin(request);storage.logout(request.cookies.get('aneira_session'));response.delete_cookie('aneira_session',path='/');return {'authenticated':False}
@app.get('/api/me')
def me(user:int=Depends(uid)):return {'authenticated':True,'user_id':user}
@app.post('/api/forgot-password')
def forgot(p:EmailOnly,request:Request):
 require_origin(request)
 token=storage.begin_reset(p.email)
 if token and all(os.environ.get(k) for k in ['ANEIRA_SMTP_HOST','ANEIRA_SMTP_USER','ANEIRA_SMTP_PASSWORD','ANEIRA_PUBLIC_URL','ANEIRA_SMTP_FROM']):
  m=EmailMessage();m['From']=os.environ['ANEIRA_SMTP_FROM'];m['To']=p.email;m['Subject']='ANEIRA password reset';m.set_content('Reset your password (expires in 15 minutes): '+os.environ['ANEIRA_PUBLIC_URL'].rstrip('/')+'/?reset='+token)
  try:
   with smtplib.SMTP_SSL(os.environ['ANEIRA_SMTP_HOST'],int(os.environ.get('ANEIRA_SMTP_PORT','465')),timeout=10) as s:s.login(os.environ['ANEIRA_SMTP_USER'],os.environ['ANEIRA_SMTP_PASSWORD']);s.send_message(m)
  except Exception:pass
 return {'message':'If this address is registered and mail is configured, a reset link will arrive shortly.'}
@app.post('/api/reset-password')
def reset(p:Reset,request:Request):
 require_origin(request)
 try:storage.complete_reset(p.token,p.password)
 except ValueError as e:raise HTTPException(400,str(e))
 return {'password_reset':True}
@app.get('/api/questions')
def questions():return {'questions':QUESTIONS,'domains':DOMAINS,'total':len(QUESTIONS)}
@app.post('/api/questions/next')
def next_questions(p:AnswerPayload):
 try:return {'initial':visible_questions(p.answers,stage='initial'),'deep':visible_questions(p.answers,stage='deep')}
 except ValueError as ex:raise HTTPException(422,str(ex))
@app.get('/api/exercises')
def exercises():return {'items':intel.EXERCISES}
@app.get('/api/journals')
def journals():return {'items':intel.JOURNALS}
@app.get('/api/chapters')
def chapters():return {'items':[{'slug':c['slug'],'title':c['title']} for c in intel.CHAPTERS]}
@app.get('/api/chapters/{slug}')
def chapter(slug:str):
 c=next((c for c in intel.CHAPTERS if c['slug']==slug),None)
 if not c:raise HTTPException(404,'Chapter unavailable')
 return c
@app.get('/api/scenarios')
def scenarios():return {'items':intel.SCENARIOS}
@app.get('/api/affirmation/follow-ups')
def affirm_followups():return {'choices':list(intel.FOLLOWUPS)}

def analysis_for(user,answers):
 previous=[x for x in storage.list_records(user,'assessment') if x['key'].startswith('assessment-')];earlier=previous[0]['data']['answers'] if previous else None
 activity=storage.list_records(user,'activity');completed=[r['data']['item_id'] for r in activity if r['data'].get('completed')]
 feedback={r['data']['item_id']:r['data'].get('helpfulness') for r in activity if r['data'].get('helpfulness') is not None}
 return intel.results(answers,earlier,completed,feedback)
@app.post('/api/assessment/results')
def assessment_results(p:AnswerPayload,user:int=Depends(uid)):
 try:return analysis_for(user,p.answers)
 except ValueError as ex:raise HTTPException(422,str(ex))
@app.post('/api/assessment/save')
def assessment_save(p:AnswerStore,request:Request,user:int=Depends(uid)):
 require_origin(request)
 if not p.consent:raise HTTPException(400,'Explicit permission to save is required')
 try:valid=validate_answers(p.answers)
 except ValueError as ex:raise HTTPException(422,str(ex))
 if not 1<=len(p.name)<=60:raise HTTPException(422,'Invalid assessment name')
 storage.save(user,'assessment',p.name,{'answers':valid,'saved_at':time.time(),'complete':len(valid)==len(QUESTIONS)})
 return {'saved':True,'name':p.name,'answered':sum(v is not None for v in valid.values())}
@app.get('/api/assessment/history')
def assessment_history(user:int=Depends(uid)):return {'items':storage.list_records(user,'assessment')}
@app.post('/api/activities/progress')
def activity_progress(p:Progress,request:Request,user:int=Depends(uid)):
 require_origin(request)
 if not p.consent:raise HTTPException(400,'Saving requires consent')
 if p.kind not in ['exercise','journal']:raise HTTPException(422,'Invalid kind')
 catalog=intel.EXERCISES if p.kind=='exercise' else intel.JOURNALS;idkey='exercise_id' if p.kind=='exercise' else 'journal_id'
 if p.item_id not in {x[idkey] for x in catalog}:raise HTTPException(422,'Unknown V3 catalog ID')
 if p.helpfulness is not None and not 0<=p.helpfulness<=5:raise HTTPException(422,'Invalid helpfulness')
 storage.save(user,'activity',p.kind+':'+p.item_id,p.model_dump())
 return {'saved':True,'id':p.item_id}
@app.get('/api/activities/progress')
def activities_progress(user:int=Depends(uid)):return {'items':storage.list_records(user,'activity')}
@app.post('/api/journals/entries')
def journal_entry(p:Entry,request:Request,user:int=Depends(uid)):
 require_origin(request)
 if not p.consent:raise HTTPException(400,'Saving requires consent')
 if p.journal_id not in {x['journal_id'] for x in intel.JOURNALS}:raise HTTPException(422,'Unknown V3 journal ID')
 if not 1<=len(p.entry_id)<=100 or len(json.dumps(p.answers))>200000:raise HTTPException(422,'Invalid entry')
 storage.save(user,'journal_entry',p.entry_id,{'journal_id':p.journal_id,'answers':p.answers,'updated_at':time.time()});return {'saved':True,'id':p.entry_id}
@app.get('/api/journals/entries')
def journal_entries(user:int=Depends(uid)):return {'items':storage.list_records(user,'journal_entry')}
@app.post('/api/cognitive/respond')
def cognitive(p:Cognitive,request:Request,user:int=Depends(uid)):
 require_origin(request);history=[r['data'] for r in storage.list_records(user,'cognitive')]
 try:out=intel.cognitive_reply(p.scenario_id,p.choice_id,history)
 except ValueError as ex:raise HTTPException(422,str(ex))
 if p.save:storage.save(user,'cognitive',str(int(time.time()*1000000)),{'scenario_id':p.scenario_id,'choice_id':p.choice_id,'timestamp':time.time()})
 return out
@app.get('/api/cognitive/history')
def cognitive_history(user:int=Depends(uid)):return {'items':storage.list_records(user,'cognitive')}
@app.post('/api/affirmation/respond')
def affirmation(p:Affirmation,request:Request,user:int=Depends(uid)):
 require_origin(request)
 if p.selection not in intel.FOLLOWUPS:raise HTTPException(422,'Invalid selection')
 if p.affirmation_id not in {'AFF-'+d.upper() for d in intel.AFFIRMATIONS}|{'AFF-CHOICE'}:raise HTTPException(422,'Unknown affirmation')
 if p.save:storage.save(user,'affirmation',str(int(time.time()*1000000)),{'affirmation_id':p.affirmation_id,'selection':p.selection,'reflection':p.reflection,'timestamp':time.time()})
 return {'follow_up':intel.FOLLOWUPS[p.selection],'saved':p.save}
@app.get('/api/progress')
def progress(user:int=Depends(uid)):
 records=storage.list_records(user);return {'assessments':[r for r in records if r['kind']=='assessment'],'completed_activities':[r for r in records if r['kind']=='activity'],'journals':[r for r in records if r['kind']=='journal_entry'],'affirmations':[r for r in records if r['kind']=='affirmation'],'cognitive':[r for r in records if r['kind']=='cognitive']}
@app.get('/api/export')
def export(user:int=Depends(uid)):return {'exported_at':time.time(),'records':storage.list_records(user)}
@app.delete('/api/records/{kind}/{key}')
def delete_record(kind:str,key:str,request:Request,user:int=Depends(uid)):
 require_origin(request)
 if kind not in ('assessment','activity','journal_entry','affirmation','cognitive'):raise HTTPException(422,'Invalid kind')
 storage.erase(user,kind,key);return {'deleted':True}
@app.delete('/api/account')
def delete_account(request:Request,user:int=Depends(uid)):
 require_origin(request);storage.delete_user(user);return {'deleted':True}
