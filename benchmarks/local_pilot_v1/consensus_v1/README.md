# Review consensus and adjudication package

This package preserves the two independent reviews and separates settled labels from unresolved evidence. No original reviewer or experiment files were modified.

| Output | Count | Status |
|---|---:|---|
| Episode labels (`episode_consensus.csv`) | 20 | Both reviewers agree on all three dimensions |
| Message labels (`message_label_consensus.csv`) | 117 | Label agreement; evidence status recorded separately |
| Message-label queue (`message_adjudication.csv`) | 183 | Unresolved; final fields blank |
| Evidence-only queue (`agreed_label_evidence_review.csv`) | 116 | Labels agree; proposal/quote references differ |

The two queues are disjoint: 299 messages require label or evidence review. Different reference sets may be complementary, not erroneous. Do not report 299 label disagreements: there are 183.

Read `ADJUDICATION_GUIDE.md` before filling worksheets. Supporting observations are in `adjudication_context.jsonl`; full packets remain in `../reviewer/`. No treatment labels or evaluator profits are included in this package. `episode_evidence.json` preserves the reviewers' separate rationales and normalizes numerical references without choosing between them.

`summary.json` records counts and SHA-256 hashes of all four source review CSVs. Consensus means agreement between reviewers, not guaranteed correctness. Status is deliberately not `adjudicated`. No detector was trained or evaluated in this step, and no experiment/API requests were made.

To reproduce into a NEW directory from the project root:

```sh
uv run python -m bond_market.reconcile_reviews benchmarks/local_pilot_v1 \
  --output benchmarks/local_pilot_v1/consensus_v2
```

The command regenerates data files, not this manually authored guide. It refuses to overwrite an existing output directory. Existing human decisions must never be overwritten by regeneration.
