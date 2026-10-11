"""ANEIRA descriptive assessment engine. No diagnoses and no aggregate trauma score."""
from __future__ import annotations
from collections import defaultdict
from pathlib import Path
import json
from datetime import datetime, timezone
DATA=Path(__file__).resolve().parent.parent/'data'
QUESTIONS=json.loads((DATA/'questions.json').read_text(encoding='utf8'))
DOMAINS=json.loads((DATA/'domains.json').read_text(encoding='utf8'))
BY_ID={q['id']:q for q in QUESTIONS}
SAFETY={'META_NECK','META_WEAPON','META_SEXUAL','META_DISTRESS'}

def validate_answers(answers:dict)->dict:
    if not isinstance(answers,dict): raise ValueError('answers must be an object')
    validated={}
    for key,value in answers.items():
        q=BY_ID.get(key)
        if q is None: raise ValueError('Unknown question')
        if value is None or value=='Prefer not to answer':
            validated[key]=None;continue
        if q['type']=='multi':
            if not isinstance(value,list) or len(value)!=len(set(value)) or any(not isinstance(v,str) or v not in q['options'] for v in value):
                raise ValueError(f'Invalid choice for {key}')
        elif not isinstance(value,str) or value not in q['options']:
            raise ValueError(f'Invalid choice for {key}')
        validated[key]=value
    return validated

def visible_questions(answers:dict, stage:str='initial', expanded_domains=None)->list:
    """Initial broad screen; optionally follow up in selected domains; always allow skip."""
    answers=validate_answers(answers)
    expanded=set(expanded_domains or [])
    if not expanded:
        expanded={d for d in DOMAINS if answers.get(DOMAINS[d]['initial_question_id']) not in (None,'Never','Not at all','Not difficult','Very confident','No') and DOMAINS[d]['initial_question_id'] in answers}
    result=[]
    for q in QUESTIONS:
        if q['stage']=='optional_support' and stage!='support':continue
        if q['stage']=='deep' and (stage=='initial' or q['domain'] not in expanded):continue
        c=q.get('show_if')
        if c and answers.get(c['question']) not in c['values']:continue
        result.append(q)
    return result

def profile(answers:dict)->dict:
    a=validate_answers(answers)
    result={}
    for d,cfg in DOMAINS.items():
        qs=[q for q in QUESTIONS if q['domain']==d]
        answered=[(q,a[q['id']]) for q in qs if q['id'] in a and a[q['id']] is not None]
        counts={'answered':len(answered),'skipped':sum(q['id'] in a and a[q['id']] is None for q in qs),'not_asked':sum(q['id'] not in a for q in qs)}
        impacts=[]; symptoms=[]; strengths=[];values={}
        for q,v in answered:
            values[q['id']]=v
            if q['type']=='impact':
                impacts.append((q['text'],q['options'].index(v)))
            elif q['type'] in ('frequency','difficulty') and q['options'].index(v)>=2:
                symptoms.append(q['text'])
            elif q['type']=='confidence':
                if q['options'].index(v)>=3: strengths.append(q['text'])
                elif q['options'].index(v)<=1: symptoms.append(q['text'])
        result[d]={'title':cfg['title'],'completion':counts,'impact_observations':impacts,'reported_difficulties':symptoms,'reported_strengths':strengths,'responses':values,'interpretation':'descriptive_original_not_clinically_validated'}
    return result

def safety_routing(answers:dict)->dict:
    a=validate_answers(answers)
    flags=[]
    for key in SAFETY:
        if a.get(key)=='Yes':flags.append({'indicator':key,'label':BY_ID[key]['text'],'path':'urgent_support_information'})
    if a.get('META_CURRENT_SUPPORT')=='Yes, urgent support':flags.append({'indicator':'META_CURRENT_SUPPORT','label':'Requested urgent confidential support','path':'urgent_support_information'})
    if a.get('PRACTICAL_01')=='Yes' or a.get('PRACTICAL_05')=='Yes':flags.append({'indicator':'ONGOING_CONCERN','label':'Current controlling behavior or unwanted contact reported','path':'confidential_support_information'})
    return {'indicators':flags,'show_support':bool(flags),'resources':{'US_domestic_violence':'https://www.thehotline.org/','US_sexual_assault':'https://rainn.org/','urgent_emergency':'Contact local emergency services if in immediate danger'},'interpretation':'indicators_are_not_a_prediction'}

def priorities(answers:dict, domain_profiles:dict)->list:
    a=validate_answers(answers)
    explicit=a.get('META_GOALS') or []
    ranked=[]
    # Human-driven priorities first; reported impact next. This is not a clinical severity score.
    keymap={'Understanding my reactions':'psychological','Body and sleep':'body','Confidence and identity':'identity','Attachment and grief':'attachment','Sexual autonomy':'sexual','Meaning and spirituality':'spiritual','Trust and connection':'social','Practical independence':'practical'}
    for goal in explicit:
        d=keymap.get(goal)
        if d and d not in ranked:ranked.append(d)
        if goal=='Body and sleep' and 'function' not in ranked:ranked.append('function')
    impact_by_domain=[]
    for d,info in domain_profiles.items():
        if info['impact_observations']:
            severity=max(s for _,s in info['impact_observations'])
            if severity>=2:impact_by_domain.append((d,severity))
    for d,_ in sorted(impact_by_domain,key=lambda x:-x[1]):
        if d not in ranked:ranked.append(d)
    return ranked

def analyze(answers:dict)->dict:
    a=validate_answers(answers)
    domains=profile(a)
    ordered=priorities(a,domains)
    strength=[{'domain':d,'statement':s} for d,v in domains.items() for s in v['reported_strengths']]
    display=[]
    for d in ordered:
        v=domains[d]
        reason= 'You chose a related goal' if d in {'psychological' if g=='Understanding my reactions' else 'body' if g=='Body and sleep' else 'identity' if g=='Confidence and identity' else 'attachment' if g=='Attachment and grief' else 'sexual' if g=='Sexual autonomy' else 'spiritual' if g=='Meaning and spirituality' else 'social' if g=='Trust and connection' else 'practical' if g=='Practical independence' else '' for g in (a.get('META_GOALS') or [])} else 'You reported an effect on daily life'
        display.append({'domain':d,'title':v['title'],'explanation':reason,'current_observations':[{'prompt':q,'reported_impact':level} for q,level in v['impact_observations']],'scientific_status':'descriptive; no neurological diagnosis inferred'})
    return {'schema':'aneira.recovery_profile.v1','domains':domains,'priorities':display,'strengths':strength,'safety_support':safety_routing(a),'preferences':{'capacity':a.get('META_CAPACITY'),'formats':a.get('META_STYLE') or []},'unanswered_are_unknown':True,'total_trauma_score':None,'message':'Your responses can help you identify areas you want to focus on. These are your reported experiences, not a diagnosis.'}

def longitudinal(earlier:dict,later:dict)->dict:
    a,b=validate_answers(earlier),validate_answers(later)
    comparable=[]
    for key in sorted(set(a)&set(b)):
        q=BY_ID[key]
        if a[key] is None or b[key] is None or q['type'] not in ('frequency','impact','confidence','difficulty'):continue
        old=q['options'].index(a[key]);new=q['options'].index(b[key])
        direction=new-old
        # A change in one answer is descriptive and not a validated clinical change.
        comparable.append({'question_id':key,'domain':q['domain'],'previous':a[key],'current':b[key],'direction':'higher_response' if direction>0 else 'lower_response' if direction<0 else 'same','change_is_not_clinically_validated':True})
    return {'comparable_items':comparable,'count':len(comparable),'excluded_noncomparable_items':len(set(a)|set(b))-len(comparable),'interpretation':'Item-level comparison only; changes are not proof of clinical improvement or regression'}
