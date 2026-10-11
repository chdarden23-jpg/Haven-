"""ANEIRA-developed descriptive interpretation, never a clinical severity instrument."""
from .engine import BY_ID, DOMAINS, validate_answers, analyze, longitudinal
from collections import defaultdict

LEVELS=('Minimal reported disruption','Mild reported disruption','Moderate reported disruption','Significant reported disruption','Severe reported disruption')
INTRO={
'cognitive':('attention, memory and decision confidence','Repeated threat and uncertainty can make concentration and choices harder. Your answers describe current difficulties; they do not measure neurological injury.'),
'body':('bodily tension and recovery after stress','A body that has spent time preparing for threat may remain alert or exhausted. Your responses describe sensations, not measured hormone levels or autonomic function.'),
'psychological':('upsetting memories, avoidance and emotional strain','Distressing reminders, self-blame and avoidance can develop in the aftermath of harmful experiences. Responsibility for another person’s choices does not belong to you.'),
'identity':('self-trust, personal choices and boundaries','When choices have been challenged or overridden, it can take practice to recognize your own wishes and trust decisions again.'),
'attachment':('longing, grief and conflicting feelings','Love, grief and recognition of harm can coexist. Missing someone does not undo the seriousness of harm or make your boundaries less meaningful.'),
'sexual':('bodily choice, consent and intimacy','Your boundaries and consent remain yours. Recovery can begin with reclaiming choice about what you discuss, explore or decline.'),
'spiritual':('meaning, belief and spiritual independence','Pressure involving beliefs can affect trust in your own meaning-making. You can define your spiritual, religious or secular life for yourself.'),
'social':('trust, connection and confidential support','Rebuilding connection can happen at a pace you choose. Trust and safety are separate from any obligation to disclose.'),
'function':('sleep, pain, fatigue and daily responsibilities','When sleep, pain or fatigue interfere with daily life, practical adjustments and appropriate healthcare can support recovery.'),
'practical':('current freedom, privacy and material needs','Ongoing monitoring, restrictions or financial instability are current circumstances, not symptoms to be explained away as trauma reactions.')}
# Descriptive thresholds, not validated psychometrics: the most disrupted response controls level;
# confidence is reverse-coded and yes/no is excluded. No inference for unanswered domains.
def disruption(q, value):
    if value is None or q['type'] not in ('impact','frequency','difficulty','confidence'):return None
    index=q['options'].index(value)
    return 4-index if q['type']=='confidence' else index

def domain_findings(answers):
    a=validate_answers(answers); out=[]
    for d,cfg in DOMAINS.items():
        observations=[]; yes=[]; strengths=[]
        for q in (q for q in BY_ID.values() if q['domain']==d):
            if q['id'] not in a or a[q['id']] is None:continue
            v=a[q['id']];level=disruption(q,v)
            if level is not None:
                observations.append({'question_id':q['id'],'question':q['text'],'answer':v,'disruption_index':level,'type':q['type']})
                if q['type']=='confidence' and level<=1:strengths.append('You reported confidence in: '+q['text'].rstrip('?').lower()+'.')
            elif q['type']=='yesno' and v=='Yes':yes.append(q['text'])
        if not observations and not yes:continue
        maximum=max((x['disruption_index'] for x in observations),default=None)
        label=LEVELS[maximum] if maximum is not None else 'Reported circumstance (not symptom-scored)'
        salient=sorted(observations,key=lambda x:-x['disruption_index'])[:3]
        topic,context=INTRO[d]
        details=' '.join('For “'+o['question']+'” you selected “'+o['answer']+'”.' for o in salient if o['disruption_index']>=2)
        if not details:details='Your responses did not indicate a high level of difficulty on the answered scaled questions in this area.'
        if yes:details+=' You also reported: '+'; '.join(yes)+'.'
        count=sum(1 for q in BY_ID.values() if q['domain']==d)
        answered=sum(1 for q in BY_ID.values() if q['domain']==d and q['id'] in a and a[q['id']] is not None)
        paragraph=f'In {cfg["title"].lower()}, your answers indicate {label.lower()} concerning {topic}. {details} {context}'
        if answered<count:paragraph+=f' You answered {answered} of {count} questions in this area, so this picture reflects only what you chose to share.'
        out.append({'domain':d,'title':cfg['title'],'severity':label,'max_disruption_index':maximum,'answered':answered,'available':count,'observations':observations,'specific_disclosures':yes,'strengths':strengths,'paragraph':paragraph})
    return out

def immediate_response(question_id,answer):
    q=BY_ID[question_id];validate_answers({question_id:answer})
    if answer is None:return None
    level=disruption(q,answer)
    if level is not None and level<2:return None
    if q['domain']=='attachment' and (level is not None and level>=2):return 'Strong feelings and awareness of harm can exist together. You do not have to resolve those feelings before choosing what supports you.'
    if q['domain']=='identity' and level is not None and level>=2:return 'Having your choices challenged or overridden can make trusting your own judgment difficult. Your preferences still deserve room and respect.'
    if q['domain']=='psychological' and ('blame' in q['text'].lower()) and level is not None and level>=2:return 'Blaming yourself can follow repeated manipulation. Another person remains responsible for the harm they chose.'
    if q['domain']=='spiritual' and answer=='Yes':return 'No one else gets to determine what you must believe. Your beliefs and values belong to you.'
    if q['domain']=='practical' and answer=='Yes':return 'Monitoring or restricting your choices is a concrete concern. Your privacy and freedom matter.'
    if level is not None and level>=2:return INTRO[q['domain']][1]
    return None

def connections(findings):
    d={x['domain']:x for x in findings if x['max_disruption_index'] is not None and x['max_disruption_index']>=2}
    rules=[({'body','cognitive','function'},'Body tension, fatigue, sleep difficulties and concentration problems may reinforce one another. This pattern can make everyday tasks harder without establishing a single biological cause.'),({'identity','attachment'},'Longing for someone and difficulty trusting your choices can coexist. Rebuilding self-trust need not depend on immediately changing how you feel about the relationship.'),({'psychological','cognitive'},'Upsetting reminders and concentration difficulties may compete for attention. A gentle, manageable pace may help with daily tasks.'),({'practical','body'},'Current external pressure can coexist with physical stress responses. Addressing practical needs and bodily comfort may require different kinds of support.'),({'spiritual','identity'},'Disruption of beliefs and self-confidence can both affect your sense of who you are. Reclaiming meaning can be part of reclaiming choice.')]
    return [text for required,text in rules if required<=set(d)]

def interpret(answers, earlier=None):
    a=validate_answers(answers);base=analyze(a); findings=domain_findings(a)
    severe=sorted((x for x in findings if x['max_disruption_index'] is not None),key=lambda x:-(x['max_disruption_index']))
    active=[x for x in severe if x['max_disruption_index']>=2]
    intro=('You shared difficulties in '+', '.join(x['title'].lower() for x in active[:3])+'. ' if active else 'You chose what to share about your current recovery. ')
    intro+='Your answers are being considered together, with your chosen goals and present circumstances, rather than reduced to one trauma score.'
    priority=base['priorities']
    priority_text=[f'{i+1}. {p["title"]}: '+('You selected this as an area of focus.' if p['explanation']=='You chose a related goal' else 'You reported interference with everyday life.') for i,p in enumerate(priority[:5])]
    reported=[q['text'] for q in BY_ID.values() if q['id'] in a and a[q['id']]=='Yes' and q['type']=='yesno' and q['domain'] in ('practical','spiritual')]
    strengths=[s for f in findings for s in f['strengths']]
    if a.get('META_GOALS'):strengths.append('You identified areas you want to work on: '+', '.join(a['META_GOALS'])+'.')
    if not strengths:strengths=['Your answers do not yet establish particular strengths; ANEIRA will not invent them. Choosing to skip questions is respected.']
    comparisons=longitudinal(earlier,a) if earlier is not None else None
    change=''
    if comparisons:
        change=f'Across {comparisons["count"]} comparable answered questions, your responses changed in different directions. Each item is shown separately; this is not a clinical recovery score.'
    return {'schema':'aneira.recovery_interpretation.v3','opening':intro,'domain_findings':findings,'cross_domain_connections':connections(findings),'reported_harmful_behaviors':reported,'strengths':strengths,'priorities':priority,'priority_explanations':priority_text,'safety_support':base['safety_support'],'preferences':base['preferences'],'progress':comparisons,'progress_explanation':change,'affirmations':['You can recognize harm and still have complicated feelings.','Your choices, boundaries and pace matter.'],'first_steps':['Choose one recovery priority that feels manageable today.','Select a suitable activity or journal entry if available; you can stop or return later.'],'closing':'Your experiences deserve to be understood in their full context. You can choose what to explore next, one step at a time.'}
