"""Validate and freeze adjudicated references without changing input reviews."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
from .reconcile_reviews import event_ids, write_csv

LABELS = {'proposal','acceptance','rejection','price_disclosure','strategy_update','other','unclear'}
# Explicitly reviewed mixed-function exception, not a generic relaxation.
MIXED = {('case_1277b44ebcf6', 14):
         'Primary acceptance also introduces a shared ask of 100, accepted by event 22; see adjudication rationale for event 22.'}


def load(path):
    return list(csv.DictReader(path.open(encoding='utf-8-sig', newline='')))


def index(rows):
    result = {(r['case_id'], int(r['event_id'])): r for r in rows}
    if len(result) != len(rows):
        raise ValueError('Duplicate message keys')
    return result


def consolidate(root, resolved, output):
    root, resolved, output = map(Path, (root, resolved, output))
    if output.exists():
        raise ValueError('Output exists; choose a new version')
    hashes = {}
    def read(path):
        hashes[str(path.resolve())] = hashlib.sha256(path.read_bytes()).hexdigest()
        return load(path)
    a = index(read(root/'reviewer A/message_review.csv'))
    b = index(read(root/'reviewer B/message_review.csv'))
    original = index(read(root/'reviewer/message_review.csv'))
    if not (a.keys() == b.keys() == original.keys()):
        raise ValueError('Reviewer and original message keys differ')
    decisions, origins = {}, {}
    for name in ('message_adjudication.csv','agreed_label_evidence_review.csv'):
        old = index(read(root/'consensus_v1'/name))
        new = index(read(resolved/name))
        if old.keys() != new.keys() or decisions.keys() & new.keys():
            raise ValueError('Missing, extra or overlapping adjudication keys')
        for key,r in new.items():
            if r['adjudication_status'] != 'adjudicated' or not r['adjudicator'].strip() or not r['adjudication_rationale'].strip():
                raise ValueError(f'Incomplete adjudication: {key}')
            for field,value in old[key].items():
                if not field.startswith(('final_','adjudication_','adjudicator')) and r[field] != value:
                    raise ValueError(f'Original review modified: {key}, {field}')
            decisions[key] = r
            origins[key] = name
    episodes = read(resolved/'episode_consensus.csv')
    if episodes != read(root/'consensus_v1/episode_consensus.csv'):
        raise ValueError('Episode consensus changed; requires separate reconciliation')
    split_by_case = {r['case_id']:r['split'] for r in episodes}
    packets = {}
    for case,split in split_by_case.items():
        path = root/'reviewer'/split/(case+'.json')
        hashes[str(path.resolve())] = hashlib.sha256(path.read_bytes()).hexdigest()
        events = json.loads(path.read_text())['events']
        packets[case] = {e['event_id']:e for e in events}
        if len(events) != len(packets[case]):
            raise ValueError('Duplicate event IDs')
    messages, provenance = [], []
    for key,r in sorted(original.items()):
        case,eid = key
        event = packets[case][eid]
        if event['type'] != 'message_sent':
            raise ValueError('Message row is not a sent message')
        for field in ('text','sender','recipient','round'):
            if str(event[field]) != r[field] or a[key][field] != r[field] or b[key][field] != r[field]:
                raise ValueError(f'Observation modified: {key}, {field}')
        decision = decisions.get(key)
        if decision:
            label = decision['final_message_label']
            links = event_ids(decision['final_linked_proposal_event_id'])
            quotes = event_ids(decision['final_quote_evidence_event_ids'])
            status, author, rationale = 'adjudicated', decision['adjudicator'], decision['adjudication_rationale']
        else:
            if any(a[key][f] != b[key][f] for f in ('message_label','linked_proposal_event_id','quote_evidence_event_ids')):
                raise ValueError(f'Unresolved unqueued message: {key}')
            label, links, quotes = a[key]['message_label'], event_ids(a[key]['linked_proposal_event_id']), event_ids(a[key]['quote_evidence_event_ids'])
            status, author, rationale = 'two_reviewer_consensus', 'reviewer_a;reviewer_b', 'Both reviewers agree on label and references; their rationales are preserved in provenance.jsonl.'
        if label not in LABELS or len(links)>1 or (label=='acceptance' and not links):
            raise ValueError(f'Invalid label or acceptance link: {key}')
        if label!='acceptance' and links:
            raise ValueError(f'Unexpected link on non-acceptance: {key}')
        for q in quotes:
            if q not in packets[case] or packets[case][q]['type']!='quote':
                raise ValueError(f'Invalid quote reference: {key}, {q}')
        deliveries = []
        for link in links:
            proposal = packets[case].get(link,{})
            deliveries = [e['event_id'] for e in packets[case].values() if e['type']=='message_delivered'
                and e['sent_event']==link and e['recipient']==event['sender']
                and e['sender']==event['recipient'] and proposal.get('round',10000)<e['round']<=event['round']]
            if proposal.get('type')!='message_sent' or proposal['sender']!=event['recipient'] or proposal['recipient']!=event['sender'] or not deliveries:
                raise ValueError(f'Invalid causal ordering/recipient link: {key}')
        messages.append({'case_id':case,'split':split_by_case[case],'event_id':eid,'round':event['round'],
            'sender':event['sender'],'recipient':event['recipient'],'text':event['text'],
            'message_label':label,'linked_proposal_event_id':links[0] if links else '',
            'proposal_delivery_event_ids':';'.join(map(str,deliveries)),
            'quote_evidence_event_ids':';'.join(map(str,quotes)),
            'proposal_bearing':label=='proposal' or key in MIXED,
            'label_status':status,'annotator':author,'rationale':rationale})
        provenance.append({'case_id':case,'event_id':eid,'reviewer_A':a[key],'reviewer_B':b[key],
                           'adjudication_source':origins.get(key),'adjudication':decision})
    final = {(r['case_id'],r['event_id']):r for r in messages}
    for r in messages:
        if r['linked_proposal_event_id']!='' and not final[r['case_id'],r['linked_proposal_event_id']]['proposal_bearing']:
            raise ValueError('Acceptance links to non-proposal without documented exception')
    output.mkdir(parents=True)
    write_csv(output/'messages.csv',messages,list(messages[0]))
    write_csv(output/'episodes.csv',episodes,list(episodes[0]))
    (output/'provenance.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in provenance))
    exceptions = [{'case_id':case,'event_id':eid,'primary_label':final[case,eid]['message_label'],'reason':reason}
                  for (case,eid),reason in MIXED.items() if (case,eid) in final]
    (output/'exceptions.json').write_text(json.dumps(exceptions,indent=2)+'\n')
    summary = {'status':'consolidated_adjudication_complete','episodes':len(episodes),'messages':len(messages),
        'message_labels':dict(Counter(r['message_label'] for r in messages)),
        'message_label_status':dict(Counter(r['label_status'] for r in messages)),
        'episode_status':'two_reviewer_consensus',
        'splits':dict(Counter(r['split'] for r in messages)),
        'mixed_function_exceptions':exceptions,'input_sha256':hashes,
        'builder_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'limitations':'Retrospective reference set, not an untouched test set. Adjudication does not establish causal harm. One message retains reviewer consensus rather than adjudicator status.'}
    (output/'manifest.json').write_text(json.dumps(summary,indent=2)+'\n')
    return {k:v for k,v in summary.items() if k not in ('input_sha256','mixed_function_exceptions')}


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('benchmark',type=Path)
    p.add_argument('--resolved',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    print(json.dumps(consolidate(args.benchmark,args.resolved,args.output),indent=2))
