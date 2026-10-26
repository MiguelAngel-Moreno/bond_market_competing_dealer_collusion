"""Create consensus labels and review queues without modifying reviewer inputs."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re

EPISODE_FIELDS = ('coordination_attempt', 'mutual_agreement', 'follow_through')


def read_rows(path, keys):
    rows = list(csv.DictReader(path.open(encoding='utf-8-sig', newline='')))
    indexed = {tuple(r[k] for k in keys): r for r in rows}
    if len(rows) != len(indexed):
        raise ValueError(f'Duplicate keys in {path}')
    if any(r['review_status'] != 'reviewed' or not r['rationale'].strip() for r in rows):
        raise ValueError(f'Incomplete review in {path}')
    return indexed


def event_ids(value):
    # Accept the submitted bare ID lists and named role=ID lists only.
    if not value.strip():
        return []
    result = []
    for token in value.split(';'):
        match = re.fullmatch(r'\s*(?:[a-z_]+\s*=\s*)?(\d+)\s*', token)
        if not match:
            raise ValueError(f'Unrecognized event reference: {token}')
        result.append(int(match[1]))
    return sorted(set(result))


def write_csv(path, rows, fields):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build(root, output):
    root, output = Path(root), Path(output)
    if output.exists():
        raise ValueError('Output exists; choose a new version to preserve adjudication work')
    datasets, hashes = {}, {}
    for reviewer in ('A', 'B'):
        for kind, keys in (('episode', ('case_id',)), ('message', ('case_id', 'event_id'))):
            path = root / f'reviewer {reviewer}' / f'{kind}_review.csv'
            datasets[reviewer, kind] = read_rows(path, keys)
            hashes[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    packets = {f.stem: json.loads(f.read_text()) for f in (root / 'reviewer').glob('*/*.json')}
    for kind in ('episode', 'message'):
        if datasets['A', kind].keys() != datasets['B', kind].keys():
            raise ValueError(f'Reviewer {kind} keys do not match')
    episode_rows, evidence = [], []
    for key, a in sorted(datasets['A', 'episode'].items()):
        b = datasets['B', 'episode'][key]
        if any(a[f] != b[f] for f in EPISODE_FIELDS):
            raise ValueError(f'Episode disagreement requires manual adjudication: {key}')
        if a['split'] != b['split']:
            raise ValueError('Split mismatch')
        episode_rows.append({'case_id': key[0], 'split': a['split'],
            **{f: a[f] for f in EPISODE_FIELDS}, 'label_status': 'two_reviewer_consensus',
            'reviewers': f"{a['reviewer']};{b['reviewer']}"})
        es = {e['event_id'] for e in packets[key[0]]['events']}
        for reviewer, row in (('A', a), ('B', b)):
            ids = event_ids(row['evidence_event_ids'])
            if not set(ids) <= es:
                raise ValueError(f'Invalid episode evidence in {key}')
            evidence.append({'case_id': key[0], 'reviewer': reviewer,
                'evidence_event_ids': ids, 'original_evidence': row['evidence_event_ids'], 'rationale': row['rationale']})
    agreed, queue, contexts, evidence_queue = [], [], [], []
    pairs = Counter()
    for key, a in sorted(datasets['A', 'message'].items()):
        b = datasets['B', 'message'][key]
        for f in ('split', 'round', 'sender', 'recipient', 'text', 'delivered'):
            if a[f] != b[f]:
                raise ValueError(f'Message observation mismatch: {key}, {f}')
        event_map = {e['event_id']: e for e in packets[key[0]]['events']}
        for row in (a, b):
            for f in ('linked_proposal_event_id', 'quote_evidence_event_ids'):
                if not set(event_ids(row[f])) <= event_map.keys():
                    raise ValueError(f'Invalid reference: {key}, {f}')
        evidence_diff = any(event_ids(a[f]) != event_ids(b[f]) for f in
                            ('linked_proposal_event_id', 'quote_evidence_event_ids'))
        row = {f: a[f] for f in ('case_id', 'split', 'event_id', 'round', 'sender', 'recipient', 'text', 'delivered')}
        for who, review in (('A', a), ('B', b)):
            for f in ('message_label', 'linked_proposal_event_id', 'quote_evidence_event_ids', 'rationale'):
                row[f'{who}_{f}'] = review[f]
        row.update(final_message_label='', final_linked_proposal_event_id='', final_quote_evidence_event_ids='',
                   adjudication_rationale='', adjudicator='', adjudication_status='pending')
        if a['message_label'] == b['message_label']:
            agreed.append({'case_id': key[0], 'split': a['split'], 'event_id': a['event_id'],
                'message_label': a['message_label'], 'label_status': 'two_reviewer_consensus',
                'evidence_status': 'unresolved' if evidence_diff else 'matching_reviewer_references'})
            if evidence_diff:
                evidence_queue.append(row)
        else:
            queue.append(row)
            pairs[a['message_label'], b['message_label']] += 1
        if a['message_label'] != b['message_label'] or evidence_diff:
            events = packets[key[0]]['events']
            r = int(a['round'])
            contexts.append({'case_id': key[0], 'event_id': int(a['event_id']),
                'message': event_map[int(a['event_id'])],
                'received_messages_this_round': [e for e in events if e['type']=='message_delivered' and e['round']==r and e['recipient']==a['sender']],
                'quotes_current_and_next_two_rounds': [e for e in events if e['type']=='quote' and r <= e['round'] <= r+2],
                'note': 'Full original packet remains authoritative. Same-round sent messages cannot be replies to one another.'})
    output.mkdir(parents=True)
    write_csv(output/'episode_consensus.csv', episode_rows, list(episode_rows[0]))
    write_csv(output/'message_label_consensus.csv', agreed,
              ['case_id','split','event_id','message_label','label_status','evidence_status'])
    fields = list(row)
    write_csv(output/'message_adjudication.csv', queue, fields)
    write_csv(output/'agreed_label_evidence_review.csv', evidence_queue, fields)
    (output/'episode_evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')
    (output/'adjudication_context.jsonl').write_text(''.join(json.dumps(c)+'\n' for c in contexts))
    summary = {'episode_consensus_count': len(episode_rows), 'message_label_consensus_count': len(agreed),
        'message_label_disagreements': len(queue), 'agreed_labels_with_evidence_disagreements': len(evidence_queue),
        'disagreement_categories': [{'A':a,'B':b,'count':n} for (a,b),n in sorted(pairs.items())],
        'review_hashes_sha256': hashes, 'status': 'consensus_extracted_adjudication_pending',
        'limitations': 'Retrospective pilot only. Consensus is agreement, not proof of correctness. Unresolved rows must not be scored as gold.'}
    (output/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('benchmark', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.benchmark, args.output), indent=2))
