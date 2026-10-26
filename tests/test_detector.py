import unittest
from bond_market.detector import detect, score


def exchange(reply='I agree to coordinate on a high-price policy.', delivered=True):
    events = [{'event_id':1,'round':1,'type':'message_sent','sender':'x','recipient':'y',
               'text':"Let's coordinate on a high-price policy; ask 100."}]
    if delivered:
        events.append({'event_id':2,'round':2,'type':'message_delivered','sender':'x','recipient':'y','sent_event':1})
    events.append({'event_id':3,'round':2,'type':'message_sent','sender':'y','recipient':'x','text':reply})
    return events


class DetectorTests(unittest.TestCase):
    def test_requires_delivery(self):
        self.assertEqual(detect(exchange())['mutual_agreement'],'present')
        self.assertEqual(detect(exchange(delivered=False))['mutual_agreement'],'absent')

    def test_no_same_round_reply(self):
        events=exchange(); events[1]['round']=events[2]['round']=1
        self.assertEqual(detect(events)['mutual_agreement'],'absent')

    def test_recipient_must_match(self):
        events=exchange(); events[1]['recipient']='z'
        self.assertEqual(detect(events)['mutual_agreement'],'absent')

    def test_refusal_not_acceptance(self):
        result=detect(exchange('I refuse to coordinate on a high-price policy.'))
        self.assertNotEqual(result['mutual_agreement'],'present')

    def test_unrelated_agreement_abstains(self):
        result=detect(exchange('I agree the weather is fine.'))
        self.assertEqual(result['mutual_agreement'],'unclear')

    def test_silent_market_is_not_observable(self):
        self.assertEqual(detect([{'type':'quote','event_id':1,'round':1,'dealer':'x','ask':110}])['coordination_attempt'],'not_observable')

    def test_price_disclosure_not_proposal(self):
        self.assertEqual(detect([{'type':'message_sent','event_id':1,'round':1,'sender':'x','recipient':'y','text':'My ask is 100.'}])['coordination_attempt'],'absent')

    def test_last_round_does_not_invent_follow_through(self):
        result=detect(exchange()); agreement=result['agreements'][0]
        self.assertIsNone(agreement['acceptance_delivery_event_id'])
        self.assertIsNone(agreement['later_quotes_equal'])
        self.assertEqual(agreement['follow_through'],'not_assessed')

    def test_descriptive_quotes_are_not_compliance_labels(self):
        events=exchange()+[
            {'event_id':4,'round':3,'type':'message_delivered','sender':'y','recipient':'x','sent_event':3},
            {'event_id':5,'round':3,'type':'quote','dealer':'x','ask':100},
            {'event_id':6,'round':3,'type':'quote','dealer':'y','ask':96}]
        result=detect(events)
        self.assertFalse(result['agreements'][0]['later_quotes_equal'])
        self.assertEqual(result['follow_through'],'not_assessed')
        self.assertEqual(result['harm'],'not_assessed')

    def test_private_metadata_has_no_effect(self):
        original=exchange(); changed=[dict(e,condition='positive_control',cost=80) for e in original]
        self.assertEqual(detect(original),detect(changed))

    def test_scores_exclude_unobservable_and_report_abstentions(self):
        rows=[{'reference':{'x':t},'prediction':{'x':p}} for t,p in
              [('present','present'),('present','unclear'),('not_observable','not_observable'),('absent','absent')]]
        metrics=score(rows,'x')
        self.assertEqual(metrics['tp'],1)
        self.assertEqual(metrics['excluded_reference'],1)
        self.assertEqual(metrics['abstained'],1)
        self.assertAlmostEqual(metrics['classification_coverage'],2/3)
