# Consolidated adjudicated reference set v1

Prepared 26 October 2026. This release consolidates the independent reviews and completed adjudication without modifying either source. It is ready for detector development and retrospective evaluation, not a claim of independently measured generalization.

| File | Purpose |
|---|---|
| `messages.csv` | All 300 messages with final primary labels, linked proposal/delivery IDs, quote references, rationale and label provenance status |
| `episodes.csv` | All 20 agreed episode judgments; unchanged from reviewer consensus |
| `provenance.jsonl` | Both original reviewers' complete rows and the adjudicator's decision for each message |
| `exceptions.json` | Documented mixed-function message interpretation |
| `manifest.json` | Release status, counts, source hashes and builder hash |

There are 15 proposals, 16 acceptances, 194 strategy updates and 75 price disclosures. Of the 300 message labels, 299 are adjudicated; one (`case_dab8a31427b8`, event 156) retains two-reviewer consensus because its label and evidence already matched. Episode labels remain `two_reviewer_consensus`; they are not falsely marked as newly adjudicated.

The split remains 180 development messages and 120 retrospective-audit messages, from 12 and 8 episodes respectively. All existing seeds have previously been inspected. Do not call the audit split an untouched test set.

## Mixed-function message

In `case_1277b44ebcf6`, event 14 retains its primary label `acceptance` while introducing a shared ask of 100. Event 22 accepts those terms. The extra `proposal_bearing` field marks event 14 as eligible to serve as a proposal antecedent without changing its primary label. All primary `proposal` rows are also proposal-bearing. This is an explicit reviewed exception, not automatic permission to treat every acceptance as a new proposal. It is reference annotation only; a detector must infer proposal-bearing content from observations rather than receive this flag as input.

## Validation and use

Before export, the builder checks original observation/reviewer fields, exact queue coverage, completion status, label validity, quote-event types, proposal recipients and delivery timing. It rejects acceptance links to messages lacking proposal-bearing status. Original inputs are hashed and final files are written into a new directory; existing releases cannot be overwritten.

Use observable packets from `../reviewer/development/` as detector inputs. Join `messages.csv` and `episodes.csv` only afterward to score predictions. Do not supply labels, rationales, proposal-bearing flags or evidence references to the detector. Treat absent/no-message episodes separately from true negative communication cases.

For detector v2, score primary message classification and exact proposal–acceptance links separately. Episode-level detection alone concealed v1's many repeated-agreement flags. Preserve this release and the v1 baseline while developing stateful handling of new terms versus maintenance of an existing policy. Economic harm and causal influence are separate outcomes, not implied by these annotations.

To reproduce into a new directory:

```sh
uv run python -m bond_market.consolidate_labels benchmarks/local_pilot_v1 \
  --resolved 'benchmarks/local_pilot_v1/consensus_v1 resolved' \
  --output benchmarks/local_pilot_v1/adjudicated_v1_repeat
```

The builder regenerates data files, not this explanatory README. The outdated pending status in the submitted snapshot's `summary.json` is preserved as historical input; the new release manifest correctly says `consolidated_adjudication_complete`.
