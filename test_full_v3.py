import os,sys,tempfile,json,zipfile,hashlib
from pathlib import Path
from cryptography.fernet import Fernet
os.environ['ANEIRA_ENCRYPTION_KEY']=Fernet.generate_key().decode()
os.environ['ANEIRA_DATABASE']=tempfile.mktemp(suffix='.sqlite3')
os.environ['ANEIRA_INSECURE_LOCAL']='1'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from fastapi.testclient import TestClient
from main import app
import intelligence as intel
import storage
from aneira_assessment.engine import QUESTIONS,DOMAINS,validate_answers,analyze,visible_questions,longitudinal,safety_routing
from aneira_assessment.interpretation import interpret,disruption

@pytest.fixture
def client():
 with TestClient(app) as c:yield c

def register(client,email):
 r=client.post('/api/register',json={'email':email,'password':'ANeira-Long-Test-Password!'});assert r.status_code==200,r.text

def answer_set(level=3):
 d={}
 for q in QUESTIONS:
  if q['type']=='multi':d[q['id']]=q['options'][:2]
  elif q['type'] in ('frequency','impact','difficulty'):d[q['id']]=q['options'][level]
  elif q['type']=='confidence':d[q['id']]=q['options'][4-level]
  else:d[q['id']]=q['options'][0]
 return d

def test_01_manifest_and_exact_counts():
 m=json.loads((Path(__file__).resolve().parents[1]/'docs/SOURCE_MANIFEST.json').read_text());assert len(m['authorized_packages'])==3
 assert len(QUESTIONS)==66 and len(DOMAINS)==10 and len(intel.EXERCISES)==45 and len(intel.JOURNALS)==41 and len(intel.CHAPTERS)==30

def test_02_unique_catalog_ids():
 for items,key in [(QUESTIONS,'id'),(intel.EXERCISES,'exercise_id'),(intel.JOURNALS,'journal_id'),(intel.CHAPTERS,'slug')]:assert len({x[key] for x in items})==len(items)

def test_03_no_legacy_activity_files():
 root=Path(__file__).resolve().parents[1]
 assert not any('activities_v2' in p.name or p.name=='recovery_engine.py' or 'existing_recovery_activities' in p.name for p in root.rglob('*'))

def test_04_image():assert (Path(__file__).resolve().parents[1]/'static/approved_homepage_user.jpeg').stat().st_size>100000

def test_05_all_answer_types():assert validate_answers(answer_set())==answer_set()

def test_06_invalid_options():
 with pytest.raises(ValueError):validate_answers({'COGNITIVE_01':'invented'})

def test_07_unknown_answers():
 with pytest.raises(ValueError):validate_answers({'BOGUS':'Yes'})

def test_08_skips_preserved():assert validate_answers({'COGNITIVE_01':None})['COGNITIVE_01'] is None

def test_09_confidence_reverse():
 q=next(q for q in QUESTIONS if q['type']=='confidence')
 assert disruption(q,q['options'][0])==4 and disruption(q,q['options'][4])==0

def test_10_yesno_not_disruption():
 q=next(q for q in QUESTIONS if q['type']=='yesno')
 assert disruption(q,q['options'][0]) is None

def test_11_priority_goals():
 a=answer_set();a['META_GOALS']=['Confidence and identity'];assert analyze(a)['priorities'][0]['domain']=='identity'

def test_12_serious_disclosure():assert safety_routing({'META_NECK':'Yes'})['show_support']

def test_13_no_invented_global_score():assert analyze(answer_set())['total_trauma_score'] is None

def test_14_branching():
 q=visible_questions({},'initial');assert q and all(x['stage']!='deep' for x in q)

def test_15_interpretation_differs():
 a=answer_set(4);b=answer_set(0)
 assert interpret(a)['opening']!=interpret(b)['opening']

def test_16_progress_same_items_only():
 a={'COGNITIVE_01':'Never','COGNITIVE_02':None};b={'COGNITIVE_01':'Often','COGNITIVE_02':'Somewhat'}
 assert longitudinal(a,b)['count']==1

def test_17_exercises_are_real():
 r=intel.results(answer_set());ids={x['exercise_id'] for x in intel.EXERCISES}
 assert r['exercise_recommendations'] and all(x['id'] in ids for x in r['exercise_recommendations'])

def test_18_journals_are_real():
 r=intel.results(answer_set());ids={x['journal_id'] for x in intel.JOURNALS}
 assert r['journal_recommendations'] and all(x['id'] in ids for x in r['journal_recommendations'])

def test_19_low_capacity_still_has_journals():
 a=answer_set();a['META_CAPACITY']='Very little'
 assert intel.results(a)['journal_recommendations']

def test_20_chapter_references_exist():
 r=intel.results(answer_set());ids={x['slug'] for x in intel.CHAPTERS};assert r['educational_recommendations'] and all(x['slug'] in ids for x in r['educational_recommendations'])

def test_21_cognitive_distinct_choices():
 s=intel.SCENARIOS[0];assert len({intel.cognitive_reply(s['id'],c['id'])['response'] for c in s['choices']})==len(s['choices'])

def test_22_cognitive_adaptive_next():
 a=intel.SCENARIOS[0];b=intel.SCENARIOS[1]
 assert intel.cognitive_reply(a['id'],'0',[{'scenario_id':b['id']}])['next_scenario_id']!=b['id']

def test_23_affirmations_distinct():assert len(set(intel.FOLLOWUPS.values()))==3

def test_24_affirmations_match_goals():
 a=answer_set();a['META_GOALS']=['Confidence and identity'];assert intel.affirmations(intel.results(a))[0]['domain']=='identity'

def test_25_registration_login_and_resume(client):
 register(client,'a25@example.com');q=answer_set();assert client.post('/api/assessment/save',json={'answers':q,'name':'current','consent':True}).status_code==200
 assert len(client.get('/api/assessment/history').json()['items'])==1
 assert client.post('/api/logout',json={}).status_code==200
 assert client.get('/api/assessment/history').status_code==401
 assert client.post('/api/login',json={'email':'a25@example.com','password':'ANeira-Long-Test-Password!'}).status_code==200
 assert client.get('/api/assessment/history').json()['items'][0]['data']['answers']==q

def test_26_account_isolation(client):
 register(client,'a26@example.com');client.post('/api/journals/entries',json={'journal_id':'AN-J001','entry_id':'private','answers':{'0':'Sensitive private words'},'consent':True})
 a=client.get('/api/journals/entries').json();assert len(a['items'])==1
 client.post('/api/logout',json={});register(client,'b26@example.com')
 assert client.get('/api/journals/entries').json()['items']==[]
 assert client.get('/api/export').json()['records']==[]
 assert client.get('/api/records/journal_entry/private').status_code==405

def test_27_encrypted_data_at_rest(client):
 register(client,'a27@example.com');client.post('/api/journals/entries',json={'journal_id':'AN-J001','entry_id':'entry1','answers':{'x':'SECRET-SURVIVOR-TEXT-ABC'},'consent':True})
 with storage.connect() as c:row=c.execute('SELECT payload FROM records WHERE kind="journal_entry"').fetchone()
 assert row and b'SECRET-SURVIVOR-TEXT-ABC' not in row['payload']

def test_28_journaling_edit_delete(client):
 register(client,'a28@example.com')
 for val in ['first','second']:
  assert client.post('/api/journals/entries',json={'journal_id':'AN-J003','entry_id':'same','answers':{'0':val},'consent':True}).status_code==200
 assert client.get('/api/journals/entries').json()['items'][0]['data']['answers']['0']=='second'
 assert client.delete('/api/records/journal_entry/same').status_code==200
 assert client.get('/api/journals/entries').json()['items']==[]

def test_29_complete_exercise(client):
 register(client,'a29@example.com');r=client.post('/api/activities/progress',json={'item_id':'AN-E001','kind':'exercise','completed':True,'helpfulness':4,'consent':True});assert r.status_code==200,r.text
 assert client.get('/api/activities/progress').json()['items'][0]['data']['helpfulness']==4

def test_30_cognitive_immediate_response(client):
 register(client,'a30@example.com');s=intel.SCENARIOS[0]
 r=client.post('/api/cognitive/respond',json={'scenario_id':s['id'],'choice_id':'1','save':True});assert r.status_code==200 and 'seriousness' in r.json()['response']
 assert len(client.get('/api/cognitive/history').json()['items'])==1

def test_31_affirmation_saves(client):
 register(client,'a31@example.com');r=client.post('/api/affirmation/respond',json={'affirmation_id':'AFF-IDENTITY','selection':'I’m beginning to believe this.','save':True});assert r.status_code==200
 assert len(client.get('/api/progress').json()['affirmations'])==1

def test_32_results_end_to_end(client):
 register(client,'a32@example.com');q=answer_set();client.post('/api/assessment/save',json={'answers':q,'consent':True});r=client.post('/api/assessment/results',json={'answers':q});assert r.status_code==200,r.text
 data=r.json();assert data['domain_findings'] and data['exercise_recommendations'] and data['journal_recommendations'] and data['educational_recommendations'] and data['personalized_affirmations']

def test_33_three_profiles_distinct():
 a=answer_set(4);b=answer_set(0);c=answer_set(2);a['META_GOALS']=['Attachment and grief'];b['META_GOALS']=['Confidence and identity'];c['META_GOALS']=['Meaning and spirituality']
 r=[intel.results(x) for x in [a,b,c]];assert len({x['opening'] for x in r})>1 and len({x['priorities'][0]['domain'] for x in r})==3

def test_34_password_reset_and_invalid_token(client):
 register(client,'a34@example.com');token=storage.begin_reset('a34@example.com')
 assert client.post('/api/reset-password',json={'token':token,'password':'AnotherSecurePass-12345'}).status_code==200
 assert client.post('/api/login',json={'email':'a34@example.com','password':'AnotherSecurePass-12345'}).status_code==200
 assert client.post('/api/reset-password',json={'token':token,'password':'YetAnotherSecurePass-12345'}).status_code==400

def test_35_delete_account_cascades(client):
 register(client,'a35@example.com');client.post('/api/assessment/save',json={'answers':answer_set(),'consent':True});assert client.delete('/api/account').status_code==200
 assert client.get('/api/progress').status_code==401

def test_36_missing_consent_blocks_storage(client):
 register(client,'a36@example.com');assert client.post('/api/assessment/save',json={'answers':{},'consent':False}).status_code==400
 assert client.post('/api/journals/entries',json={'journal_id':'AN-J001','entry_id':'a','consent':False}).status_code==400

def test_37_routes_and_assets(client):
 assert client.get('/').status_code==200 and b'ANEIRA' in client.get('/').content
 for path in ['/health','/api/questions','/api/exercises','/api/journals','/api/chapters','/api/scenarios','/static/app.js','/static/theme.css','/static/approved_homepage_user.jpeg']:
  assert client.get(path).status_code==200,path

def test_38_100percent_preserve_hashes():
 root=Path(__file__).resolve().parents[1];m=json.loads((root/'docs/SOURCE_MANIFEST.json').read_text())
 for v in m['retained_files']:
  p=root/v['destination'];assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==v['sha256']

def test_39_sensitive_entries_excluded_logs(client,capsys):
 register(client,'a39@example.com');client.post('/api/journals/entries',json={'journal_id':'AN-J001','entry_id':'private','answers':{'secret':'DO-NOT-LOG-THIS-SECRET-911'},'consent':True});assert 'DO-NOT-LOG-THIS-SECRET-911' not in capsys.readouterr().out

def test_40_reassessment_changes_recs(client):
 register(client,'a40@example.com');a=answer_set(3);a['META_GOALS']=['Confidence and identity'];r1=client.post('/api/assessment/results',json={'answers':a}).json();a['META_GOALS']=['Attachment and grief'];r2=client.post('/api/assessment/results',json={'answers':a}).json();assert r1['priorities'][0]['domain']!=r2['priorities'][0]['domain']
