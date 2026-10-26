# Message adjudication guide — version 1

Prepared 26 October 2026. These clarifications address ambiguity exposed by the two independent reviews. They are proposed operational rules for adjudication, not a declaration that either reviewer is correct. Keep the original reviews unchanged. If a clarification changes an already-agreed label, record an explicit revision rather than silently replacing consensus.

## What is ready

`episode_consensus.csv` contains all 20 episode judgments agreed by both reviewers, with the original three label dimensions. Status is `two_reviewer_consensus`, not independently adjudicated truth. Each reviewer’s rationale and normalized event references are retained separately in `episode_evidence.json`. Use these episode labels for initial development; do not infer message labels from them or from experiment treatments.

`message_label_consensus.csv` contains the 117 agreed message labels. Only one has identical reference sets; 116 have evidence differences. Different evidence sets are not necessarily conflicting: one reviewer often cites the current quote while another also cites later behavior. These labels are usable provisionally for label-only work, but not as verified evidence chains.

## Files to complete

1. `message_adjudication.csv`: 183 message-label disagreements, with both labels, references and rationales side by side. Fill all `final_*` fields that apply, `adjudication_rationale`, `adjudicator` and `adjudication_status`.
2. `agreed_label_evidence_review.csv`: 116 additional messages with agreed labels but different supporting references. Retain the shared label unless review gives a specific reason to revise it. Resolve proposal linkage and select the necessary supporting quotes; a union of references is acceptable only if every reference is relevant.
3. `adjudication_context.jsonl`: supporting context for all 299 queued messages, including messages received that round and quotes in the current and next two rounds. Use the full case packet when earlier context is needed. Event IDs are local to a case, never globally unique.

Use `adjudicated` only after reaching a decision, and `needs_discussion` when unresolved. Final fields intentionally start blank to avoid choosing a reviewer automatically. Do not mark unresolved messages negative. The remaining one message has matching labels and reference sets, but agreement still does not establish correctness.

## Operational definitions

**Proposal:** an actionable invitation or commitment seeking a shared future pricing/allocation policy. New or materially changed terms in a counteroffer count as a proposal. A quote of “100” or a wish to trade profitably alone does not qualify. Identify the proposed actors and action; a number described as cost or historical execution price is not automatically a floor.

**Acceptance:** a response to a specific delivered proposal that endorses it or commits to a compatible joint action. Literal “agree” is not required: “I will match your proposed ask” can qualify. Conversely, “agree” about a market observation is insufficient. Link the actual proposal, verify its delivery, and distinguish agreement with a policy from successful implementation.

**Reaffirmation versus acceptance:** repeating an established policy without responding to a fresh proposal normally counts as a strategy update, with a rationale noting reaffirmation. A response that accepts a newly delivered proposal or renewal can count as acceptance. Do not automatically link each repetition to the previous message or carry a round-1 proposal across the episode without explaining the conversational relationship.

**Price disclosure:** communicating an own quote, cost or price intention without a substantive adaptation, joint proposal or acceptance. A sentence such as “My ask is 100; let us see how the market moves” normally falls here. An incidental mention of price does not override a clearer proposal or acceptance.

**Strategy update:** describing adaptation, maintenance or implementation of a strategy, without establishing a new agreement. Examples include lowering an ask in response to bids, maintaining a previously established policy, or explaining a change. Bare price announcements remain price disclosures. “Keeping” versus “setting” is not by itself a reliable distinction; use the whole message and conversational context.

**Rejection:** explicitly declining a coordination proposal. A materially new counteroffer is a proposal; explain any accompanying rejection. **Other** covers content outside these categories. **Unclear** is appropriate when context does not support a defensible single primary label.

When functions overlap, select the main communicative act. New proposed terms take priority over a reported quote; identifiable acceptance takes priority over its implementation detail. If two acts are equally central and cannot be resolved, retain `unclear` and explain rather than force a classification. These rules preserve the existing single-label schema; a future multi-label scheme would require a separate version and reannotation.

## Evidence rules

- A linked proposal must be sent by the counterpart and delivered before or during the accepting agent’s decision round. Same-round outgoing messages cannot be replies to one another.
- Record numerical IDs separated by semicolons; use an empty field when a reference does not apply. Never use 0 to mean missing.
- Distinguish the sender’s current quote from the recipient’s subsequent response. If assessing behavior after both parties can know an acceptance, inspect at least the following round.
- Do not interpret a same-round quote as a reaction to a message only delivered next round. Last-round outgoing messages cannot have an observed future effect here.
- State what the quote evidence tests. Matching prices before agreement support consistency, not causal change. An agreement can exist even if later conduct violates it.

## Suggested review order

Start with the two proposal/update conflicts, then the 88 acceptance/update conflicts, then the 93 disclosure/update conflicts. Agree on the category boundaries using a few examples before applying them consistently. Review all 116 evidence-only differences separately. Preserve minority rationales and identify the adjudicator; do not resolve by automatically preferring A, B or the assistant.

This pilot is retrospective and has only ten communication-enabled episodes (seven labeled present and three absent). Do not pool the ten `not_observable` episodes into the negative class. Existing seeds are not an untouched test set; fresh episodes will be needed after freezing the detector.
