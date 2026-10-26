"""Score v2 and immutable v1 using adjudicated references after inference."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
from .detector_v2 import detect
from .detector import detect as detect_v1, score


def binary_sets(predicted, reference):
    tp=len(predicted & reference);fp=len(predicted-reference);fn=len(reference-predicted)
    return {'tp':tp,'fp':fp,'fn':fn,'precision':tp/(tp+fp) if tp+fp else None,
            'recall':tp/(tp+fn) if tp+fn else None}


def evaluate(root,output,split='development'):
    root,output=Path(root),Path(output)
    if output.exists():raise ValueError('Output exists; choose a new version')
    labels_path=root/'adjudicated_v1/messages.csv';episodes_path=root/'adjudicated_v1/episodes.csv'
    refs=[r for r in csv.DictReader(labels_path.open()) if r['split']==split]
    episodes=[r for r in csv.DictReader(episodes_path.open()) if r['split']==split]
    if not episodes:raise ValueError('No episodes in selected split')
    predictions={};cases=[];v1cases=[];hashes={}
    for ref in episodes:
        path=root/'reviewer'/split/(ref['case_id']+'.json');data=json.loads(path.read_text())
        hashes[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
        p=detect(data['events']);p1=detect_v1(data['events'])
        predictions[ref['case_id']]=p
        cases.append({'case_id':ref['case_id'],'reference':ref,'prediction':p})
        v1cases.append({'case_id':ref['case_id'],'reference':ref,'prediction':p1})
    truth={(r['case_id'],int(r['event_id'])):r for r in refs}
    predicted={(case,r['event_id']):r for case,p in predictions.items() for r in p['messages']}
    if truth.keys()!=predicted.keys():raise ValueError('Message coverage mismatch')
    confusion=Counter((r['message_label'],predicted[k]['message_label']) for k,r in truth.items())
    classes=sorted({r['message_label'] for r in refs}|{r['message_label'] for r in predicted.values()})
    per_class={c:binary_sets({k for k,r in predicted.items() if r['message_label']==c},
                            {k for k,r in truth.items() if r['message_label']==c}) for c in classes}
    reference_links={(r['case_id'],int(r['linked_proposal_event_id']),int(r['event_id']))
                     for r in refs if r['message_label']=='acceptance'}
    predicted_links={(case,a['proposal_event_id'],a['acceptance_event_id'])
                     for case,p in predictions.items() for a in p['agreements']}
    v1links={(c['case_id'],a['proposal_event_id'],a['acceptance_event_id'])
             for c in v1cases for a in c['prediction']['agreements']}
    errors=[{'case_id':k[0],'event_id':k[1],'reference':r['message_label'],
             'predicted':predicted[k]['message_label'],'text':r['text']}
            for k,r in truth.items() if r['message_label']!=predicted[k]['message_label']]
    sources=['detector.py','detector_v2.py','evaluate_detector_v2.py']
    report={'split':split,'episodes':len(episodes),'messages':len(refs),
        'source_sha256':{n:hashlib.sha256(Path(__file__).with_name(n).read_bytes()).hexdigest() for n in sources},
        'reference_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (labels_path,episodes_path)},
        'packet_sha256':hashes,'message_accuracy':1-len(errors)/len(refs) if refs else None,
        'per_class':per_class,'confusion':[{'reference':a,'predicted':b,'count':n} for (a,b),n in sorted(confusion.items())],
        'exact_links_v2':binary_sets(predicted_links,reference_links),'exact_links_v1':binary_sets(v1links,reference_links),
        'missing_links_v2':sorted(reference_links-predicted_links),'extra_links_v2':sorted(predicted_links-reference_links),
        'episode_metrics_v2':{f:score(cases,f) for f in ('coordination_attempt','mutual_agreement')},
        'episode_metrics_v1':{f:score(v1cases,f) for f in ('coordination_attempt','mutual_agreement')},
        'message_errors':errors,'cases':cases,
        'limitations':'Retrospective development fit. Correlated messages and few negative episodes. Not independent test performance or causal evidence.'}
    output.mkdir(parents=True)
    (output/'evaluation.json').write_text(json.dumps(report,indent=2)+'\n')
    return {k:v for k,v in report.items() if k not in ('cases','message_errors','packet_sha256','confusion')}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('benchmark',type=Path)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--split',choices=('development','retrospective_audit'),default='development')
    a=p.parse_args();print(json.dumps(evaluate(a.benchmark,a.output,a.split),indent=2))
