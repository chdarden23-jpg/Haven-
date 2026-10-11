"""V3-only orchestration. Only the authorized source databases are referenced."""
import json
from pathlib import Path
from aneira_assessment.engine import validate_answers, QUESTIONS, DOMAINS, longitudinal
from aneira_assessment.interpretation import interpret
ROOT=Path(__file__).resolve().parent
EXERCISES=json.loads((ROOT/'data/exercise_master.json').read_text())
JOURNALS=json.loads((ROOT/'data/journaling_library.json').read_text())
CHAPTERS=json.loads((ROOT/'data/chapters.json').read_text())
QMAP={q['id']:q for q in QUESTIONS}
# Crosswalk is routing metadata, not changes to any original activity or assessment.
CROSSWALK={'cognitive':{'attention','memory','executive_function','cognitive','judgment','decision'},'body':{'hypervigilance','somatic','sleep','arousal','fatigue','body'},'psychological':{'trauma','shame','self_blame','anxiety','depression','emotion','regulation'},'identity':{'identity','autonomy','boundaries','self_trust','self_worth','values','confidence','judgment'},'attachment':{'attachment','grief','separation','loss'},'sexual':{'sexual','consent','bodily_autonomy'},'spiritual':{'spiritual','meaning','beliefs'},'social':{'social','trust','relationships','boundaries'},'function':{'sleep','routine','fatigue','activity','executive_function','pain'},'practical':{'autonomy','financial','safety','practical'},'support':{'social','safety'},'preferences':set()}

def tags(value):
 if isinstance(value,str):return {value.lower().replace(' ','_')}
 return {str(v).lower().replace(' ','_') for v in value or []}

def rank_catalog(report,kind='exercise',completed=None,feedback=None):
 completed=set(completed or []);feedback=feedback or {}
 collection=EXERCISES if kind=='exercise' else JOURNALS
 ranked=[];order=[v['domain'] for v in report['priorities']]
 energy=report['preferences'].get('capacity'); formats=tags(report['preferences'].get('formats'))
 for item in collection:
  ident=item['exercise_id'] if kind=='exercise' else item['journal_id']
  itemtags=tags(item.get('domains',[]) if kind=='exercise' else [item.get('domain')]);itemtags|=tags(item.get('targets',[]))
  matched=[d for d in order if d in itemtags or CROSSWALK.get(d,set())&itemtags]
  if not matched:continue
  if energy=='Very little' and kind=='exercise' and (item.get('suggested_duration_minutes') or 0)>10:continue
  # Low capacity changes pacing; it must not eliminate every optional journal choice.
  if kind=='exercise' and item.get('arousal_suitability')=='hyperarousal' and report['preferences'].get('capacity')=='Very little':continue
  score=sum((len(order)-order.index(d))*3 for d in matched)
  score-=8 if ident in completed else 0
  score+=(feedback.get(ident,0)-2)*2 if ident in feedback else 0
  ranked.append({'id':ident,'title':item['title'],'score':score,'domains':matched,'why':'Chosen because '+', '.join(DOMAINS[d]['title'].lower() for d in matched[:2])+' relates to your selected priorities.','kind':kind})
 return sorted(ranked,key=lambda x:(-x['score'],x['id']))

def chapter_recs(report):
  terms={'cognitive':['brain','memory','cognit','attention'],'body':['nervous','body','stress','sleep'],'psychological':['trauma','abuse','emotional'],'identity':['identity','autonomy','confidence'],'attachment':['attachment','bond','grief','separation'],'sexual':['sexual','consent','coercion'],'spiritual':['spirit','religio','meaning'],'social':['isolat','support','relation'],'function':['function','health','sleep'],'practical':['control','financial','safety','technology']}
  rec=[]
  for ch in CHAPTERS:
   hay=(ch['title']+' '+ch.get('original_section','')).lower()
   matched=[d for d in [x['domain'] for x in report['priorities']] if any(t in hay for t in terms.get(d,[]))]
   if matched:rec.append({'slug':ch['slug'],'title':ch['title'],'matched_domains':matched,'reason':'Related to '+DOMAINS[matched[0]]['title']})
  return sorted(rec,key=lambda x:(len(x['matched_domains'])*-1,x['title']))[:8]

AFFIRMATIONS={
 'cognitive':('I can make space to think at my own pace.','Your mind deserves patience while you rebuild concentration.'),
 'body':('I can choose comfort and gentleness with my body.','Small, comfortable adjustments count.'),
 'psychological':('The responsibility for harmful behavior belongs to the person who chose it.','Your emotions do not have to follow a timetable.'),
 'identity':('My preferences matter, even when others disagree.','One small independent choice can be enough today.'),
 'attachment':('I can miss someone while honoring what I know.','Conflicting feelings do not invalidate your experience.'),
 'sexual':('My body and my consent belong to me.','You are entitled to change your mind.'),
 'spiritual':('I have the freedom to choose what gives my life meaning.','Your beliefs and values are yours to define.'),
 'social':('I can decide whom I trust and what I share.','Boundaries are not obligations to explain yourself.'),
 'function':('I can adapt my day to the energy I have.','Progress can include rest and practical support.'),
 'practical':('I am allowed to seek practical help and privacy.','Support is a resource, not a test of independence.')}
FOLLOWUPS={
 'I believe this.':'You recognize this as true for you. What helps you hold onto that understanding?',
 'I’m beginning to believe this.':'Something about this is starting to fit. Which part feels most believable today?',
 'I want to believe this, but I’m not there yet.':'You do not need to force agreement. Is there a gentler version of this statement that feels possible?'}

def affirmations(report):
 return [{'id':'AFF-'+v['domain'].upper(),'domain':v['domain'],'text':AFFIRMATIONS[v['domain']][0],'context':AFFIRMATIONS[v['domain']][1]} for v in report['priorities'] if v['domain'] in AFFIRMATIONS] or [{'id':'AFF-CHOICE','domain':'identity','text':AFFIRMATIONS['identity'][0],'context':AFFIRMATIONS['identity'][1]}]

def results(answers, earlier=None, completed=None, feedback=None):
 a=validate_answers(answers);r=interpret(a,earlier)
 r['exercise_recommendations']=rank_catalog(r,'exercise',completed,feedback)[:10]
 r['journal_recommendations']=rank_catalog(r,'journal',completed,feedback)[:8]
 r['educational_recommendations']=chapter_recs(r)
 r['personalized_affirmations']=affirmations(r)
 r['next_steps']=[{'kind':'exercise','id':x['id'],'title':x['title'],'why':x['why']} for x in r['exercise_recommendations'][:2]]+[{'kind':'journal','id':x['id'],'title':x['title'],'why':x['why']} for x in r['journal_recommendations'][:1]]
 return r

# Original, V3-only interactive cognitive education with per-selection immediate interpretations.
SCENARIO_TOPICS=[
 ('threats','A partner repeatedly intimidated or threatened you, then became affectionate. What best describes your reaction?',[
 ('I know threats are serious, but the affection confuses me.','Affection afterward does not cancel a threat. It can create conflicting emotional messages. You can recognize both without treating the threat as acceptable.'),
 ('I understand it happened, but I do not feel its seriousness.','Intellectual recognition and emotional integration can unfold differently. Familiarity with threats does not reduce their seriousness; no particular emotion is required.'),
 ('Maybe the threats happened because I upset them.','Responsibility for threats belongs to the person who made them. Disagreement or conflict does not authorize intimidation.'),
 ('I can recognize the threat without minimizing it.','You are separating the actual behavior from what followed it. That distinction can support your own judgment.')]),
 ('humiliation','Someone repeatedly humiliated you, apologized, and later did it again. What fits best?',[
 ('The apologies make me doubt whether it counts.','An apology can matter while repeated humiliation remains harmful. Repetition is relevant to evaluating behavior.'),('I think I should have handled it better.','Someone else choosing humiliation is not your responsibility to prevent through perfect reactions.'),('I know it is wrong, but it feels normal now.','Repeated exposure can make harmful conduct familiar. Familiarity does not make it respectful.'),('I want to name the repeated pattern.','Naming the repetition is one way to trust observations over isolated promises.')]),
 ('control','A partner restricted your contacts while saying it was love or protection. What fits?',[
 ('I assumed the restriction proved they cared.','Care and restricting a person’s freedom are different behaviors. The language of love does not turn coercion into consent.'),('I knew it was controlling but struggled to resist.','Difficulty resisting does not make the restriction voluntary or deserved.'),('I worry I caused their jealousy.','Another person is responsible for how they respond to insecurity. Their feelings do not transfer ownership of your choices.'),('I want to rebuild my choices.','Rebuilding choice can begin with small decisions that belong entirely to you.')]),
 ('selfblame','You remember a harmful interaction and wonder whether you caused it. Which response is closest?',[
 ('If I had spoken differently, it might not have happened.','You can reflect on communication without assuming responsibility for another person’s harmful decisions.'),('I understand their reasons, so I excuse it.','Understanding an explanation is not the same as agreeing that the behavior was acceptable.'),('I blame myself even when I know better.','Automatic self-blame can persist after intellectual understanding shifts. You do not have to fight the feeling to recognize responsibility clearly.'),('I am learning to separate our responsibilities.','Distinguishing responsibilities supports more accurate appraisal of what happened.')]),
 ('attachment','You miss someone who repeatedly hurt you. What is most difficult?',[
 ('Missing them makes me question whether it was abuse.','Longing is a feeling, not evidence that abusive conduct was harmless.'),('I remember the good times more vividly.','Positive memories and harmful experiences can both be real. One does not erase the other.'),('I feel both love and anger.','Love and anger can coexist without requiring an immediate resolution.'),('I want to respect both my grief and my boundaries.','Grief does not require abandoning boundaries or denying what happened.')]),
 ('memory','You find yourself doubting an event you once recognized clearly. What happens next?',[
 ('I trust the other person’s version more than mine.','Repeated contradiction can interfere with confidence. You may take your own recollections seriously without needing to prove every detail.'),('I cannot remember every detail, so I dismiss it.','Incomplete memory does not make an event acceptable or require self-blame.'),('I go over it again and again.','Repeated checking can be exhausting. Choosing to pause does not mean choosing denial.'),('I focus on what I can establish.','Separating observed facts from unresolved details can make room for clearer judgment.')]),
 ('boundaries','You say no to a request and the other person becomes angry. What do you think?',[
 ('Their anger means my boundary was unfair.','Another person’s disappointment does not by itself make a boundary unreasonable.'),('I feel compelled to reverse my decision.','Pressure can complicate choice. You are allowed to take time before deciding.'),('I want to avoid all disagreements.','Avoidance can serve a protective purpose while also becoming exhausting. You can choose the pace of future boundary practice.'),('I can respect the no I gave.','Respecting your own limit is meaningful even when it feels unfamiliar.')]),
 ('minimization','A harmful pattern lasted a long time, but parts of it now seem ordinary. What fits?',[
 ('Other people had it worse.','The seriousness of harmful behavior does not depend on comparison with someone else.'),('Nothing terrible happened every day.','Periods without harm do not erase harmful incidents or patterns.'),('I know the facts but feel emotionally numb.','Feeling numb does not change what occurred. Recognition need not produce a specific emotional reaction.'),('I can describe events without exaggerating or minimizing.','Precise naming respects your experience without requiring dramatic language.')]),
 ('responsibility','You understand why someone behaved cruelly. How do you interpret that?',[
 ('Their background excuses their behavior.','Personal history can help explain behavior without removing responsibility for present choices.'),('I feel responsible for helping them change.','Caring for someone does not oblige you to accept harm or become responsible for their change.'),('I can understand them and still reject the conduct.','Explanations and accountability can both exist.'),('I am unsure where their responsibility begins.','Consider separating the circumstance from the choice: what did they choose to do, and who controlled that choice?')]),
 ('autonomy','You have the chance to make an independent decision. What comes up?',[
 ('I worry choosing for myself is selfish.','Having preferences is not selfish. Making a choice for yourself can be ordinary autonomy.'),('I keep looking for permission.','Permission-seeking can become familiar under control. You can practice small choices without judging yourself.'),('I cannot easily identify what I want.','Not knowing immediately is allowed. Exploring options without pressure is a form of choice.'),('I would like to try a small decision.','Small self-directed decisions offer opportunities to notice what matters to you.')])]
SCENARIOS=[{'id':'REC-'+topic.upper(),'topic':topic,'prompt':prompt,'choices':[{'id':str(i),'text':label,'response':response,'follow_up':'What part of this explanation would you like to explore, or would you prefer to move on?'} for i,(label,response) in enumerate(choices)]} for topic,prompt,choices in SCENARIO_TOPICS]

def cognitive_reply(scenario_id,choice_id,history=None):
 s=next((s for s in SCENARIOS if s['id']==scenario_id),None)
 if s is None:raise ValueError('Unknown scenario')
 c=next((x for x in s['choices'] if x['id']==str(choice_id)),None)
 if c is None:raise ValueError('Unknown response')
 used={h.get('scenario_id') for h in history or []}
 nextone=next((x for x in SCENARIOS if x['id'] not in used and x['id']!=scenario_id),None)
 return {'scenario_id':scenario_id,'choice_id':c['id'],'response':c['response'],'follow_up':c['follow_up'],'next_scenario_id':nextone['id'] if nextone else None,'recognition_topic':s['topic'],'not_graded':True}
