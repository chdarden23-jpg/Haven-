"""ANEIRA V3 transparent, deterministic, non-diagnostic activity recommender."""
import json
from pathlib import Path
from dataclasses import dataclass,field
from typing import Optional
ROOT=Path(__file__).parent
EXERCISES=json.loads((ROOT/'exercise_master.json').read_text())
DOMAIN_ALIASES={'difficulty concentrating':'executive_function','mental fatigue':'executive_function','hypervigilance':'hypervigilance','panic':'anxiety','emotional numbness':'dissociation','shutdown':'dissociation','loss of identity':'identity','self blame':'shame','attachment':'attachment','longing':'attachment','grief':'grief','sleep difficulties':'sleep','sexual boundaries':'sexual_autonomy','spiritual recovery':'spiritual_identity','decision confidence':'autonomy','PTSD symptoms':'ptsd'}
@dataclass
class Preferences:
    difficulties:list[str]
    goals:list[str]=field(default_factory=list)
    arousal:str='unspecified' # hyper, numb, both, unspecified
    excluded_ids:list[str]=field(default_factory=list)
    uncomfortable_formats:list[str]=field(default_factory=list)
    history:list[dict]=field(default_factory=list)
    limit:int=5

def normalize(s):return DOMAIN_ALIASES.get(s.casefold().strip(),s.casefold().strip().replace(' ','_'))
def recommend(p:Preferences):
    domains={normalize(s) for s in p.difficulties+p.goals}
    scored=[]
    for e in EXERCISES:
        if e['exercise_id'] in p.excluded_ids or e['software']['screen_type'] in p.uncomfortable_formats:continue
        overlap=domains.intersection(e['domains'])
        if not overlap:continue
        if p.arousal in ('hyper','numb') and e['arousal_suitability'] not in (p.arousal,'both'):continue
        feedback=[h for h in p.history if h.get('exercise_id')==e['exercise_id']]
        # no clinical inference; only user-supplied helpfulness and explicit choices
        last=feedback[-1] if feedback else {}
        if last.get('uncomfortable') is True:continue
        helpfulness=last.get('helpfulness')
        if helpfulness is not None and (not isinstance(helpfulness,(int,float)) or not 0<=helpfulness<=5):helpfulness=None
        score=10*len(overlap)+e['evidence']['score']/100+(helpfulness-2.5)*.1 if helpfulness is not None else 10*len(overlap)+e['evidence']['score']/100
        scored.append((score,e))
    scored.sort(key=lambda t:(-t[0],t[1]['exercise_id']))
    return [{'exercise_id':e['exercise_id'],'title':e['title'],'why_recommended':f'Matches your selected area: {", ".join(sorted(domains.intersection(e["domains"])))}, with a low-intensity, optional activity.','steps':e['instructions'],'duration_minutes':e['suggested_duration_minutes'],'alternatives_available':True,'skip_or_stop_anytime':True,'evidence_level':e['evidence']['rating'],'software':e['software']} for _,e in scored[:max(0,min(p.limit,20))]]
def record_activity(exercise_id, completed=None, helpfulness=None, uncomfortable=False):
    if exercise_id not in {e['exercise_id'] for e in EXERCISES}:raise ValueError('Unknown exercise')
    if helpfulness is not None and (not isinstance(helpfulness,int) or not 0<=helpfulness<=5):raise ValueError('Helpfulness must be 0-5')
    return {'exercise_id':exercise_id,'completed':completed,'helpfulness':helpfulness,'uncomfortable':bool(uncomfortable),'diagnosis':None,'neurobiological_inference':None}
if __name__=='__main__':
    for q in [Preferences(['difficulty concentrating']),Preferences(['hypervigilance'],arousal='hyper'),Preferences(['emotional numbness'],arousal='numb'),Preferences(['loss of identity','grief'])]:
        print(q.difficulties,[x['title'] for x in recommend(q)])
