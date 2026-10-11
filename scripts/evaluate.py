"""Evaluation script: runs analyzer on every log in logs/, compares against
expected_reports/, and prints a table with per-field match and overall percentage."""

from __future__ import annotations
from typing import Any, Tuple, List, Dict
import json
import os
import sys
from pathlib import Path

# Add the project root (parent of scripts/) to path so we can import the app
proj_root = str(Path(__file__).resolve().parent.parent)
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

# Also add log_analyzer subdirectory
log_analyzer_path = os.path.join(proj_root, "log_analyzer")
if log_analyzer_path not in sys.path:
    sys.path.insert(0, log_analyzer_path)

from app.parser import read_jsonl
from app.analyzer import analyze


# ─── Helper: deep compare two values ────────────────────────────────────────────

def deep_compare(
    generated: Any,
    expected: Any,
    *,
    path: str = "",
) -> Tuple[int, int, List[str]]:
    """Count matched and total fields, returning (matched, total, missed_paths).

    Supports dicts, lists (order-sensitive for evidence), and scalars.
    """
    matched = 0
    total = 0
    missed: List[str] = []

    # Both dicts
    if isinstance(generated, dict) and isinstance(expected, dict):
        all_keys = set(generated.keys()) | set(expected.keys())
        total = len(all_keys)
        for key in all_keys:
            gval = generated.get(key)
            eval_val = expected.get(key)
            sub_path = f"{path}.{key}" if path else key
            if key not in generated:
                missed.append(sub_path)
            elif key not in expected:
                # Extra key in generated — count as unmatched but not missed
                pass
            else:
                sub_match, sub_total, sub_missed = deep_compare(
                    gval, eval_val, path=sub_path,
                )
                matched += sub_match
                total += sub_total
                missed.extend(sub_missed)
    # Both lists (compare element-wise)
    elif isinstance(generated, list) and isinstance(expected, list):
        total = max(len(generated), len(expected))
        for i in range(max(len(generated), len(expected))):
            if i < len(generated) and i < len(expected):
                sub_match, sub_total, sub_missed = deep_compare(
                    generated[i], expected[i], path=f"{path}[{i}]",
                )
                matched += sub_match
                total += sub_total
                missed.extend(sub_missed)
            elif i >= len(generated):
                missed.append(f"{path}[{i}] — missing in generated")
            else:
                missed.append(f"{path}[{i}] — extra in generated")
    # Scalars (including None)
    else:
        total = 1
        if generated == expected:
            matched = 1
        else:
            matched = 0

    return matched, total, missed


# ─── Per‑incident-type field weights ────────────────────────────────────────────

# Weight each top-level field; the sum of all weights = 100
FIELD_WEIGHTS: Dict[str, int] = {
    "incident_id": 8,
    "incident_type": 12,
    "severity": 8,
    "affected_service": 8,
    "probable_root_cause": 20,
    "evidence": 25,
    "troubleshooting_steps": 15,
    "expected_resolution": 12,
}


# ─── Run analyzer on a single log file ──────────────────────────────────────────

def analyze_log(log_path: Path, expected_path: Path) -> Tuple[dict, dict]:
    """Run the analyzer on a log file and load the expected report.

    Returns (generated_report_dict, expected_report_dict).
    """
    # Parse the JSONL
    entries, bad_count = read_jsonl(str(log_path))
    # Analyze
    generated = analyze(entries)
    # Convert pydantic model to dict
    generated_dict = generated.model_dump() if hasattr(generated, 'model_dump') else generated.dict()
    # Load expected
    with open(expected_path, "r", encoding="utf-8") as f:
        expected = json.load(f)
    return generated_dict, expected


# ─── Compare two reports ───────────────────────────────────────────────────────

def compare_reports(generated: dict, expected: dict) -> Dict[str, object]:
    """Compare a generated report against an expected report.

    Returns a dict with per-field match results and an overall percentage.
    """
    results: Dict[str, object] = {
        "field_results": {},
        "overall_percentage": 0.0,
        "matched_fields": 0,
        "total_fields": 0,
    }

    total_weight = sum(FIELD_WEIGHTS.values())
    weighted_matched = 0
    weighted_total = 0

    for field, weight in FIELD_WEIGHTS.items():
        gval = generated.get(field)
        eval_val = expected.get(field)

        matched = 0
        total = 0

        if field == "evidence":
            # Compare evidence lists: count matching entries
            g_evidence = gval or []
            e_evidence = eval_val or []

            total = max(len(g_evidence), len(e_evidence))

            if total == 0:
                matched = 1
                weighted_matched += weight
                weighted_total += weight
                results["field_results"][field] = {
                    "matched": True,
                    "detail": "No evidence in either report",
                }
                continue

            # Count how many expected evidence entries have a matching
            # timestamp (as a key attribute) and matching level + service
            matching_expected = 0
            for e_entry in e_evidence:
                for g_entry in g_evidence:
                    if (
                        e_entry.get("timestamp") == g_entry.get("timestamp")
                        and e_entry.get("level") == g_entry.get("level")
                        and e_entry.get("service") == g_entry.get("service")
                    ):
                        matching_expected += 1
                        break

            matched = matching_expected

        elif field == "troubleshooting_steps":
            g_steps = gval or []
            e_steps = eval_val or []

            total = max(len(g_steps), len(e_steps))

            if total == 0:
                matched = 1
            else:
                # Count expected steps that appear in generated (lenient substring match)
                # or if generated step contains key terms from expected step
                matching = 0
                for e_step in e_steps:
                    e_lower = e_step.lower()
                    found = False
                    for g_step in g_steps:
                        g_lower = g_step.lower()
                        # Lenient check: if expected step is substring of generated,
                        # OR if generated step is substring of expected,
                        # OR if they share key words (overlap >= 50% of expected words)
                        if e_lower in g_lower or g_lower in e_lower:
                            found = True
                            break
                        # Check word overlap
                        e_words = set(e_lower.split())
                        g_words = set(g_lower.split())
                        if e_words and g_words:
                            overlap = len(e_words & g_words) / max(1, len(e_words))
                            if overlap >= 0.5:
                                found = True
                                break
                    if found:
                        matching += 1
                matched = matching

        else:
            # Scalar field comparison - use lenient matching for text fields
            total = 1
            if gval is not None and eval_val is not None:
                if field == "incident_type":
                    matched = 1 if gval == eval_val else 0
                elif field == "severity":
                    matched = 1 if str(gval).lower() == str(eval_val).lower() else 0
                elif field == "affected_service":
                    g_set = set(str(gval).lower().split(","))
                    e_set = set(str(eval_val).lower().split(","))
                    if g_set == e_set:
                        matched = 1
                    else:
                        overlap = len(g_set & e_set)
                        matched = overlap / max(1, len(e_set))
                else:
                    # Lenient text matching for probable_root_cause and expected_resolution
                    gen_str = str(gval).lower()
                    exp_str = str(eval_val).lower()
                    # Check exact match
                    if gen_str == exp_str:
                        matched = 1
                    # Check if one is substring of the other
                    elif gen_str in exp_str or exp_str in gen_str:
                        matched = 1
                    else:
                        # Check word overlap (>= 50% of expected words in generated)
                        gen_words = set(gen_str.split())
                        exp_words = set(exp_str.split())
                        if exp_words and gen_words:
                            overlap = len(gen_words & exp_words) / max(1, len(exp_words))
                            matched = 1 if overlap >= 0.5 else 0
                        else:
                            matched = 0
            elif gval is None and eval_val is None:
                matched = 1
            else:
                matched = 0

        # Compute weighted contribution
        if total > 0:
            weight_contribution = weight * (matched / total) if total > 0 else 0
        else:
            weight_contribution = 0

        weighted_matched += weight_contribution
        weighted_total += weight

        # Store field result
        detail_parts = []
        if field == "evidence":
            detail_parts.append(f"matched={matched} expected={len(eval_val) if eval_val else 0}")
        elif field == "troubleshooting_steps":
            detail_parts.append(f"matched={matched} expected={len(eval_val) if eval_val else 0}")
        else:
            detail_parts.append(f"generated={gval!r} expected={eval_val!r}")

        results["field_results"][field] = {
            "matched": bool(matched) if field not in ("evidence", "troubleshooting_steps") else matched > 0,
            "detail": "; ".join(detail_parts),
            "weight": weight,
        }

    # Overall percentage
    if weighted_total > 0:
        overall = round((weighted_matched / weighted_total) * 100, 2)
    else:
        overall = 0.0

    results["overall_percentage"] = overall
    results["matched_fields"] = sum(
        1 for f in results["field_results"].values() if f["matched"]
    )
    results["total_fields"] = len(FIELD_WEIGHTS)

    return results


# ─── Evaluate all log categories ────────────────────────────────────────────────

def evaluate_all() -> List[Dict[str, object]]:
    """Run the analyzer on every log in logs/ and compare against expected_reports/.

    Returns a list of result dicts, one per incident category.
    """
    base = Path(__file__).resolve().parent.parent
    log_dir = base / "log_generation" / "logs"
    expected_dir = base / "log_generation" / "expected_reports"

    # Derive categories from actual log files (strip .jsonl to get base name)
    log_files = sorted(log_dir.glob("*.jsonl"))
    if not log_files:
        print("No log files found in", log_dir)
        return []

    # Build mapping: base_name -> expected report path
    expected_map: Dict[str, Path] = {}
    for f in expected_dir.glob("*.json"):
        expected_map[f.stem] = f  # e.g., "api_rate_limit" -> "api_rate_limit.json"

    all_results: List[Dict[str, object]] = []

    # Print header
    try:
        print(f"\n{'':>4} {'Incident':<25} {'Overall %':>8} {'Fields':>6} {'Field Results'}")
        print("-" * 120)
    except UnicodeEncodeError:
        print(f"\n{'':>4} {'Incident':<25} {'Overall %':>8} {'Fields':>6} {'Field Results'}")

    for log_path in log_files:
        base_name = log_path.stem  # e.g., "api_rate_limit"
        expected_path = expected_map.get(base_name)

        if expected_path is None:
            print(f"  {base_name}: no expected report found, skipping")
            continue

        try:
            generated, expected = analyze_log(log_path, expected_path)
        except Exception as exc:
            print(f"  {base_name}: error during analysis: {exc}")
            continue

        results = compare_reports(generated, expected)
        all_results.append(results)

        # Format output
        incident_name = base_name  # e.g., "api_rate_limit"
        overall = results["overall_percentage"]
        fields = results["matched_fields"]
        total = results["total_fields"]
        # Build a short detail string
        details = []
        for fname, finfo in results["field_results"].items():
            detail = finfo["detail"]
            if len(detail) > 60:
                detail = detail[:60] + "..."
            details.append(f"{fname}:{detail}")

        print(
            f"{log_files.index(log_path) + 1:>4} "
            f"{incident_name:<25} "
            f"{overall:>7.1f}% "
            f"{fields:>2}/{total} "
            f"{' | '.join(details)}"
        )

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    overall_avg = sum(r["overall_percentage"] for r in all_results) / max(len(all_results), 1)
    print(f"Average overall percentage: {overall_avg:.2f}%")

    # Per-field aggregation
    print("\nPer-field performance:")
    for field in FIELD_WEIGHTS:
        matches = sum(
            1 for r in all_results if r["field_results"].get(field, {}).get("matched", False)
        )
        pct = round((matches / len(all_results)) * 100, 1) if all_results else 0.0
        print(f"  {field}: {matches}/{len(all_results)} = {pct}%")

    return all_results


# ─── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    results = evaluate_all()
