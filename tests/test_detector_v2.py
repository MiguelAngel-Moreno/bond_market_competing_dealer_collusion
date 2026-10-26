import unittest
from bond_market.detector_v2 import detect
from bond_market.evaluate_detector_v2 import binary_sets


def message(i,r,s,t):
    return {'type':'message_sent','event_id':i,'round':r,'sender':s,'recipient':'b' if s=='a' else 'a','text':t}
def delivery(i,r,m):
    return {'type':'message_delivered','event_id':i,'round':r,'sent_event':m['event_id'],'sender':m['sender'],'recipient':m['recipient']}


class StatefulDetectorTests(unittest.TestCase):
    def test_acceptance_once_then_reaffirmation(self):
        p=message(1,1,'a',"Let's coordinate on a high-price policy.")
        a=message(3,2,'b','I agree to coordinate on a high-price policy. Let\'s keep our asks aligned.')
        repeat=message(5,3,'b',a['text'])
        result=detect([p,delivery(2,2,p),a,delivery(4,3,a),repeat])
        self.assertEqual([m['message_label'] for m in result['messages']],['proposal','acceptance','strategy_update'])
        self.assertEqual(len(result['agreements']),1)

    def test_new_shared_terms_not_echoed_as_new_proposal(self):
        p=message(1,1,'a',"Let's coordinate on prices.")
        a=message(3,2,'b','I agree to coordinate on prices. Let\'s aim for a shared ask of 100.')
        b=message(5,3,'a',a['text'])
        out=detect([p,delivery(2,2,p),a,delivery(4,3,a),b])
        self.assertTrue(out['messages'][1]['proposal_bearing'])
        self.assertFalse(out['messages'][2]['proposal_bearing'])
        self.assertEqual(out['messages'][2]['linked_proposal_event_id'],3)

    def test_explicit_renewal_can_receive_new_acceptance(self):
        p=message(1,1,'a',"Let's maintain our ask at 99.")
        a=message(3,2,'b',"I'll keep my ask at 99 as suggested.")
        renewal=message(5,3,'a',"Let's keep our asks aligned at 99.")
        reply=message(7,4,'b',a['text'])
        out=detect([p,delivery(2,2,p),a,delivery(4,3,a),renewal,delivery(6,4,renewal),reply])
        self.assertEqual([a['proposal_event_id'] for a in out['agreements']],[1,5])

    def test_delivery_and_round_boundaries(self):
        p=message(1,1,'a',"Let's coordinate on prices.");a=message(3,1,'b','I agree to coordinate on prices.')
        self.assertFalse(detect([p,delivery(2,1,p),a])['agreements'])
        a['round']=2
        self.assertFalse(detect([p,a])['agreements'])

    def test_refusal_and_unrelated_agreement(self):
        p=message(1,1,'a',"Let's coordinate on prices.")
        for text in ('I refuse to coordinate on prices.','I agree the weather is nice.'):
            self.assertFalse(detect([p,delivery(2,2,p),message(3,2,'b',text)])['agreements'])

    def test_no_case_identifiers_or_private_values_needed(self):
        e=message(1,1,'a','My ask is 100.')
        self.assertEqual(detect([e]),detect([{**e,'condition':'positive_control','cost':80}]))
        self.assertEqual(detect([])['coordination_attempt'],'not_observable')

    def test_link_scoring_penalizes_wrong_antecedent(self):
        result=binary_sets({('x',2,4)},{('x',1,4)})
        self.assertEqual((result['tp'],result['fp'],result['fn']),(0,1,1))
