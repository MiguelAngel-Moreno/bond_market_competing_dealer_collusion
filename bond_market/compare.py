"""Compare completed, matched four-condition episodes; no significance claims."""
import argparse
import json
from pathlib import Path
from .experiment import CONDITIONS


def compare(root):
    groups = {}
    for path in sorted(Path(root).glob("*/manifest.json")):
        manifest = json.loads(path.read_text())
        if manifest["status"] != "completed":
            continue
        # Never mix mock/real, models, source revisions or episode lengths.
        signature = json.dumps({k: manifest[k] for k in
                               ("config", "mock", "rounds", "source_sha256")}, sort_keys=True)
        group = groups.setdefault((signature, manifest["seed"]), {})
        condition = manifest["condition"]
        if condition in group:
            raise ValueError(f"Duplicate {condition} for seed {manifest['seed']}; use a fresh output directory for each batch")
        group[condition] = json.loads((path.parent / "metrics.json").read_text())
    comparisons = []
    for (signature, seed), group in groups.items():
        missing = sorted(set(CONDITIONS) - set(group))
        if missing:
            comparisons.append({"seed": seed, "settings": json.loads(signature), "missing": missing})
            continue
        baseline = group["independent"]
        deltas = {condition: {
            "buyer_surplus_loss_vs_independent": baseline["buyer_surplus"] - metrics["buyer_surplus"],
            "seller_profit_gain_vs_independent": metrics["seller_profit"] - baseline["seller_profit"],
            "total_surplus_change_vs_independent": metrics["total_surplus"] - baseline["total_surplus"],
            "trade_count_change_vs_independent": metrics["trade_count"] - baseline["trade_count"],
        } for condition, metrics in group.items()}
        # Outcome interaction: joint objective's effect with vs without communication.
        interaction = {field: (group["positive_control"][field] - group["objective_only"][field])
                       - (group["communication_control"][field] - baseline[field])
                       for field in ("buyer_surplus", "seller_profit", "total_surplus", "trade_count")}
        comparisons.append({"seed": seed, "settings": json.loads(signature),
                            "conditions": group, "deltas": deltas, "factorial_interaction": interaction})
    return {"comparisons": comparisons, "interpretation":
            "Descriptive paired episode results only. Positive buyer_surplus_loss means buyer harm. "
            "Factorial interaction is an outcome difference, not proof of collusion. "
            "Model sampling is not seeded; seeds match costs, buyer values and bids only."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    print(json.dumps(compare(args.directory), indent=2))
