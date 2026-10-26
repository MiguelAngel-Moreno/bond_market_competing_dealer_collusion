# Local pilot detection benchmark v1

This snapshot contains **20 real episodes, 300 sent messages and 20 provisional assistant episode annotations**. No additional inference calls were made. Original run outputs are untouched.

Start with `reviewer/RUBRIC.md`. Give independent reviewers ONLY `reviewer/`; keep `evaluator_only/` separate. The full transcripts are available as Markdown and machine-readable JSON. Blank episode/message CSV worksheets avoid anchoring reviewers to the assistant's suggestions.

## Contents

- `reviewer/development/`: 12 opaque-ID cases from seeds 1–3.
- `reviewer/retrospective_audit/`: 8 opaque-ID cases from seeds 4–5.
- `reviewer/episode_review.csv`: 20 episode-level review rows.
- `reviewer/message_review.csv`: 300 message review rows with delivery status.
- `evaluator_only/provisional_episode_labels.json` and `.csv`: assistant judgments, evidence event IDs, rationales and uncertainty. These are NOT adjudicated gold labels.
- `evaluator_only/source_mapping.json`: original paths, conditions, seeds and SHA-256 hashes for traceability. Never input this into a detector.
- `evaluator_only/economics.csv`: original outcomes plus designated-pair and outsider profits. Never input this into a message detector.
- `ANALYSIS.md`: findings and limitations.

The assistant saw original treatment labels and outcomes before annotating. The provisional labels are therefore not blind or independent. Blinding packets for later reviewers does not erase that limitation. Annotations are episode-level; the message worksheet is deliberately blank, not falsely presented as 300 individually reviewed labels.

**There is no clean held-out test set in this pilot:** all five seeds have already been inspected. The 12/8 division is a retrospective development/audit split only. Freeze the detector after development and collect fresh seeds (for example 6–15) before claiming generalization. Keep whole seeds across all conditions together; never randomly split messages from the same episode across train/test. Repeated wording across seeds further limits independence.

The existing numeric-floor screen is unchanged. Do not tune it and then call the assistant annotations an independent validation set. Its output of zero flags is recorded as a coverage limitation, not a calibrated false-negative rate. The target "explicit coordination attempt" is broader than its original numeric-floor target.

## Re-export

From the project directory:

```sh
uv run python -m bond_market.benchmark outputs/local_pilot --output benchmarks/local_pilot_v2
```

The exporter refuses to overwrite an existing destination and rejects duplicate completed seed/condition episodes or mock episodes. It exports fresh blank worksheets and evaluator economics; it does not invent reviewed labels or copy hand annotations from v1. New snapshots require their own review. Original input event hashes are recorded for provenance.

## Next step

Have two independent reviewers use fresh worksheet copies, reconcile disagreements, then develop a proposal/acceptance/action extractor from the development cases. Retain ambiguous cases and negative examples. Score it on independently adjudicated labels, and reserve fresh runs for final testing. No production detector, legal conclusion or causal intervention is implemented by this export.
