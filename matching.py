"""Matching contract for a future evidence-reviewed external activity library."""
from .engine import analyze

def match_candidates(assessment:dict, catalog:list)->list:
    """Catalog uses external IDs; never invent IDs. Missing catalog => no suggestions."""
    report=analyze(assessment)
    priorities={v['domain']:i for i,v in enumerate(report['priorities'])}
    formats=set(report['preferences']['formats'])
    result=[]
    for a in catalog:
        if not isinstance(a,dict) or not all(k in a for k in ('id','title','domains','evidence_refs','formats','status')):raise ValueError('Incomplete external activity record')
        if not a['evidence_refs'] or a['status'] not in ('reviewed','developmental'):continue
        relevant=[d for d in a['domains'] if d in priorities]
        if not relevant:continue
        if a.get('requires_reflection') and report['preferences']['capacity']=='Very little':continue
        if formats and not formats.intersection(a['formats']) and 'Not sure' not in formats:continue
        result.append({'id':a['id'],'title':a['title'],'matched_domains':relevant,'reason':'Related to '+', '.join(report['domains'][d]['title'] for d in relevant),'evidence_refs':a['evidence_refs'],'adaptation_status':a['status'],'priority_order':min(priorities[d] for d in relevant)})
    return sorted(result,key=lambda x:(x['priority_order'],x['title']))
