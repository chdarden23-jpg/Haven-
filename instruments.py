"""Rights-aware instrument scoring: explicitly gated. No copyrighted content included."""
import json
from pathlib import Path
REGISTRY={i['id']:i for i in json.loads((Path(__file__).parent.parent/'data'/'instrument_registry.json').read_text())}

def score_instrument(name:str,responses:list,*,authorized:bool=False,qualified_interpreter:bool=False)->dict:
    if name not in REGISTRY:raise ValueError('Unregistered instrument')
    item=REGISTRY[name]
    if not authorized or not qualified_interpreter:raise PermissionError('Explicit license/use-context authorization and qualified interpretation required')
    if name=='PCL-5':
        if len(responses)!=20 or any(type(v)!=int or v not in range(5) for v in responses):raise ValueError('Complete twenty 0–4 symptom ratings required')
        clusters={'B':sum(responses[:5]),'C':sum(responses[5:7]),'D':sum(responses[7:14]),'E':sum(responses[14:])}
        return {'instrument':name,'score':sum(responses),'possible_range':[0,80],'clusters':clusters,'status':'symptom_score_not_diagnosis'}
    if name=='PC-PTSD-5':
        if len(responses)!=5 or any(type(v)!=bool for v in responses):raise ValueError('Five boolean item responses required, exposure screen must be administered separately')
        return {'instrument':name,'score':sum(responses),'possible_range':[0,5],'status':'screen_not_diagnosis','exposure_screen_required':True}
    if name=='PHQ-9':
        if len(responses)!=9 or any(type(v)!=int or v not in range(4) for v in responses):raise ValueError('Nine complete 0–3 responses required')
        return {'instrument':name,'score':sum(responses),'possible_range':[0,27],'item9_endorsed':responses[8]>0,'status':'symptom_screen_not_diagnosis'}
    if name=='GAD-7':
        if len(responses)!=7 or any(type(v)!=int or v not in range(4) for v in responses):raise ValueError('Seven complete 0–3 responses required')
        return {'instrument':name,'score':sum(responses),'possible_range':[0,21],'status':'symptom_screen_not_diagnosis'}
    if name=='WHO-5':
        if len(responses)!=5 or any(type(v)!=int or v not in range(6) for v in responses):raise ValueError('Five complete 0–5 responses required')
        return {'instrument':name,'raw_score':sum(responses),'score':sum(responses)*4,'possible_range':[0,100],'status':'wellbeing_measure_not_diagnosis'}
    raise NotImplementedError('Published algorithm has not been sufficiently verified and enabled for this package')
