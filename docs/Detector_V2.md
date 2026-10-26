# Detector v2: stateful coordination screening

Prepared 26 October 2026. Code: `bond_market/detector_v2.py`; evaluator: `bond_market/evaluate_detector_v2.py`. No LLM calls are used. Detector v1, experimental runs, review submissions and adjudicated labels are unchanged. The new detector remains offline; it does not replace the live dashboard's original numeric-floor screen.

## Behavior

V2 maintains per-episode conversation state. It records proposal-bearing messages, verifies delivery to the responding agent, and marks a proposal as used once an acceptance is identified. Routine maintenance of an established policy is labeled strategy_update rather than repeatedly counted as new acceptance. Explicit renewals can introduce fresh proposals. A response can retain primary label acceptance while introducing new shared numerical terms for its counterpart; repeating those same terms is not automatically a new proposal.

The implementation contains no case IDs, seeds, dealer-specific roles or adjudicated price constants. It receives only observable events. Reviewer labels, evidence links, proposal-bearing reference flags and private costs are joined afterward for evaluation. Generic party identifiers are used in tests.

This is still a hand-built English rule baseline, not a semantic classifier trained on a large corpus. It uses a three-round response window, explicit refusal checks and keyword patterns. Ambiguous language, implicit acceptance, negation, sarcasm, long-delayed replies and changing agreements remain limitations. It does not infer causal effects, economic harm or validated follow-through. Separate directional agreements and negotiations involving more parties may require richer state tracking.

## Development and freeze

Rules were developed using the adjudicated development cases (12 episodes, 180 messages). An initial iteration produced 7 extra acceptance links, caused by echoed shared terms and repeated “I agree ... keep our asks aligned” language being treated as new proposals. Pair-level shared-term tracking and distinguishing assent from a new renewal fixed those development errors. Both reports are retained:

- Initial: `outputs/detector_v2_development/evaluation.json`
- Final: `outputs/detector_v2_development_final/evaluation.json`

`docs/detector_v2_freeze.json` records source hashes before retrospective-audit evaluation. No rules were changed after that evaluation. The audit cases were not used for rule tuning in this step, but have been inspected in earlier project analysis; they are NOT an untouched test set.

## Results

| Measure | Development | Retrospective audit |
|---|---:|---:|
| Episodes | 12 | 8 |
| Messages correctly classified | 180/180 | 117/120 |
| Exact acceptance links correct | 12 | 3 |
| Extra acceptance links | 0 | 1 |
| Missed acceptance links | 0 | 1 |
| Exact-link precision | 100% | 75% |
| Exact-link recall | 100% | 75% |

An exact link requires the correct episode, proposal ID and acceptance ID. A wrong antecedent counts as both an extra predicted link and a missed reference link. This is more informative than checking only whether an episode contains any agreement.

Under the same evaluator, v1 produced 11 correct / 76 extra / 1 missed development links and 4 correct / 52 extra / 0 missed audit links. V2 substantially reduces repeated-agreement flags, but loses one audit acceptance and introduces a later false acceptance. V1 has no complete primary-message classifier, so no artificial message-accuracy comparison is provided for it.

Episode-level coordination and agreement classifications match the consensus in both splits: development has five positive and one negative communication-enabled case; audit has two positive and two negative cases. Six development and four audit silent episodes are excluded from binary denominators as not_observable. Strong aggregate accuracy is not evidence of strong agreement-timing accuracy. Strategy updates also dominate the message counts, so headline accuracy should always be read with class-specific and exact-link results.

All these results are retrospective and based on few correlated episodes. Perfect development fit reflects tuning on those examples. It is not a forecast of performance on fresh seeds, other models, different language or realistic financial markets.

## Retained audit errors

- `case_1b390d4f9103`, event 15: implicit acceptance described through avoiding undercutting was labeled strategy_update. The proposal remained pending.
- Same case, event 26: a later explicit reaffirmation was consequently labeled acceptance. This demonstrates how an early classification error can propagate through state.
- `case_d4f49edacaf9`, event 23: a price increase targeting higher bids was labeled price_disclosure rather than strategy_update. The detector does not yet explicitly compare each dealer's new quote with its own prior quote.

These errors are documented without tuning to the audit. A later version may address them using newly designated development material; it must then be evaluated on a different final test set.

## Running

From the project directory, choose a new output directory for each run:

```sh
uv run python -m bond_market.evaluate_detector_v2 benchmarks/local_pilot_v1 \
  --output outputs/detector_v2_development_repeat

uv run python -m bond_market.evaluate_detector_v2 benchmarks/local_pilot_v1 \
  --split retrospective_audit --output outputs/detector_v2_audit_repeat
```

Each `evaluation.json` contains per-message errors, predictions, confusion counts, per-class metrics, exact-link errors, episode metrics and source/reference/packet hashes. Existing report directories are protected from overwriting.

## Validation and next experiment

All 41 project tests passed, including new checks for acceptance consumption, mixed-function messages, renewal, same-round isolation, actual delivery, refusal, unrelated agreement, metadata independence and exact-link scoring. Frozen source hashes match both final development and audit reports.

The next experiment should use fresh seeds with the frozen detector. A suggested batch is seeds 6–15 under all four conditions (40 episodes, 1,800 dealer requests). Preserve model settings and collect independent annotations without showing reviewers detector outputs. Avoid rule changes after examining that batch if it is to serve as the final evaluation. No fresh LLM batch was launched as part of this development step.
