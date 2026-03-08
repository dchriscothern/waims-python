"""
research_merge.py
=================
Merges a newly fetched research_log (extended lookback) into your existing
research_log.json without overwriting any decisions you have already made.

Usage:
    python research_merge.py --new research_log_extended.json --existing research_log.json

What it does:
    1. Loads your existing log (with all your decisions intact)
    2. Loads the new extended log
    3. For each paper in the new log:
       - If it already exists in your existing log (matched by PMID or URL) → SKIP (keep your decision)
       - If it is NEW and passes the relevance filter → add it as PENDING
       - If it is NEW but fails the relevance filter → discard silently
    4. Writes the merged result back to research_log.json (backs up original first)

Relevance filter (tightened from original monitor):
    Keeps papers that mention sport science / performance monitoring topics.
    Rejects papers that are purely clinical medicine with no performance relevance.
"""

import json
import argparse
import shutil
from pathlib import Path
from datetime import datetime

# ==============================================================================
# RELEVANCE FILTER
# ==============================================================================
# These are the terms we WANT — sport science and performance monitoring focus
INCLUDE_TERMS = [
    # Core monitoring
    "athlete monitoring", "readiness", "wellness questionnaire", "training load",
    "workload", "player load", "acute chronic", "acwr",
    # Sleep / recovery
    "sleep", "recovery", "fatigue", "overreach", "overtraining",
    # Neuromuscular
    "countermovement jump", "cmj", "force plate", "reactive strength",
    "neuromuscular fatigue", "jump height",
    # GPS / physical metrics
    "gps", "accelerometer", "player tracking", "high speed running",
    "deceleration", "acceleration", "sprint",
    # Injury risk
    "injury prevention", "injury risk", "acl", "hamstring", "soft tissue",
    "load management", "return to play",
    # Female athlete specific
    "female athlete", "women's basketball", "wnba", "female basketball",
    "menstrual cycle", "hormonal", "female sport",
    # Sport science methods
    "z-score", "baseline", "individual response", "principal component",
    "pca", "machine learning", "predictive model", "sport science",
    # Basketball specific
    "basketball", "nba", "elite basketball", "back to back",
]

# These terms flag a paper as likely clinical medicine / not relevant
EXCLUDE_TERMS = [
    "surgery", "surgical", "pharmacolog", "drug", "medication", "clinical trial",
    "randomized controlled trial", "placebo", "biopsy", "histolog",
    "patholog", "radiology", "mri diagnosis", "ultrasound diagnosis",
    "cancer", "tumor", "oncolog", "cardiac arrest", "sepsis", "icu",
    "pediatric patient", "hospital", "inpatient", "outpatient clinic",
    "anesthesia", "rehabilitation patient",  # rehab in clinical sense
    "occupational therapy", "physical therapy patient",
    "post-operative", "preoperative",
]

# Journals that are almost always relevant — skip extra filtering
ALWAYS_RELEVANT_JOURNALS = [
    "british journal of sports medicine", "bjsm",
    "international journal of sports physiology",
    "journal of strength and conditioning",
    "sports medicine", "journal of sports sciences",
    "medicine and science in sports",
    "frontiers in sports",
    "journal of science and medicine in sport",
    "european journal of sport science",
    "journal of athletic training",
    "plos one",  # keep if title passes
]

# Journals that are almost always clinical — apply strict filter
CLINICAL_JOURNALS = [
    "new england journal", "lancet", "jama", "bmj",
    "annals of internal medicine", "circulation",
    "journal of bone and joint surgery",  # unless basketball injury
    "american journal of sports medicine",  # keep if basketball/load related
    "clinical journal of sport medicine",
]


def relevance_score(paper: dict) -> tuple[int, str]:
    """
    Returns (score, reason).
    score >= 2  → include
    score == 1  → borderline (include with low priority note)
    score == 0  → exclude
    """
    title   = (paper.get("title", "") or "").lower()
    abstract = (paper.get("abstract", "") or "").lower()
    journal  = (paper.get("journal", "") or "").lower()
    text     = f"{title} {abstract}"

    # Hard exclude: clinical journals + clinical terms in title
    for excl in EXCLUDE_TERMS:
        if excl in title:
            return 0, f"Excluded: clinical term '{excl}' in title"

    # Always relevant journals get a free pass if title has any sport term
    for rel_j in ALWAYS_RELEVANT_JOURNALS:
        if rel_j in journal:
            sport_in_title = any(t in title for t in ["athlete", "sport", "basketball", "load", "sleep", "jump", "gps", "fitness", "exercise", "training"])
            if sport_in_title:
                return 3, f"Always-relevant journal: {journal}"

    # Count include term hits
    hits = [t for t in INCLUDE_TERMS if t in text]
    score = len(hits)

    # Bonus: title hit is worth more than abstract hit
    title_hits = [t for t in INCLUDE_TERMS if t in title]
    score += len(title_hits)

    if score >= 4:
        return 2, f"Strong match: {', '.join(title_hits[:3])}"
    elif score >= 2:
        return 1, f"Borderline: {', '.join(hits[:3])}"
    else:
        return 0, f"No relevant terms found (score={score})"


def get_paper_id(paper: dict) -> str:
    """Unique identifier — prefer PMID, fall back to URL, then title."""
    return (
        str(paper.get("pmid", ""))
        or str(paper.get("id", ""))
        or str(paper.get("url", ""))
        or str(paper.get("title", ""))[:80]
    )


def merge_logs(existing_path: Path, new_path: Path, min_score: int = 1) -> dict:
    """
    Returns summary dict with merge statistics.
    Writes merged result to existing_path (backs up original).
    """

    # Load existing
    with open(existing_path, "r", encoding="utf-8") as f:
        existing = json.load(f)

    # Load new
    with open(new_path, "r", encoding="utf-8") as f:
        new_papers = json.load(f)

    # Build lookup of existing paper IDs
    existing_ids = {get_paper_id(p) for p in existing}

    # Stats
    stats = {
        "existing_count":  len(existing),
        "new_candidates":  len(new_papers),
        "already_present": 0,
        "added":           0,
        "filtered_out":    0,
        "borderline":      0,
        "added_papers":    [],
        "filtered_papers": [],
    }

    for paper in new_papers:
        pid = get_paper_id(paper)

        # Already in existing log — skip, preserve decision
        if pid in existing_ids:
            stats["already_present"] += 1
            continue

        # Score for relevance
        score, reason = relevance_score(paper)

        if score >= min_score:
            # Add as PENDING with relevance note
            paper["decision"]       = "PENDING"
            paper["relevance_score"] = score
            paper["relevance_note"]  = reason
            paper["date_merged"]     = datetime.now().strftime("%Y-%m-%d")
            existing.append(paper)
            existing_ids.add(pid)
            stats["added"] += 1
            stats["added_papers"].append(paper.get("title", "?")[:80])
            if score == 1:
                stats["borderline"] += 1
        else:
            stats["filtered_out"] += 1
            stats["filtered_papers"].append({
                "title":  paper.get("title", "?")[:80],
                "reason": reason,
            })

    # Backup original before writing
    backup_path = existing_path.with_suffix(f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    shutil.copy(existing_path, backup_path)
    print(f"Backup saved: {backup_path}")

    # Write merged
    with open(existing_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    stats["final_count"] = len(existing)
    return stats


# ==============================================================================
# CLI
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Merge extended research log into existing, preserving decisions.")
    parser.add_argument("--new",      required=True, help="Path to newly fetched log (e.g. research_log_extended.json)")
    parser.add_argument("--existing", default="research_log.json", help="Path to existing log (default: research_log.json)")
    parser.add_argument("--min-score", type=int, default=1,
                        help="Minimum relevance score to include (1=borderline+strong, 2=strong only). Default: 1")
    parser.add_argument("--strict", action="store_true",
                        help="Only include strong matches (score >= 2). Equivalent to --min-score 2")
    args = parser.parse_args()

    existing_path = Path(args.existing)
    new_path      = Path(args.new)

    if not existing_path.exists():
        print(f"ERROR: Existing log not found: {existing_path}")
        return
    if not new_path.exists():
        print(f"ERROR: New log not found: {new_path}")
        return

    min_score = 2 if args.strict else args.min_score

    print(f"\nMerging {new_path} → {existing_path}")
    print(f"Relevance filter: min score = {min_score} ({'strict' if min_score >= 2 else 'borderline+strong'})\n")

    stats = merge_logs(existing_path, new_path, min_score=min_score)

    print("=" * 60)
    print("MERGE COMPLETE")
    print("=" * 60)
    print(f"  Existing papers (before):  {stats['existing_count']}")
    print(f"  New candidates scanned:    {stats['new_candidates']}")
    print(f"  Already present (skipped): {stats['already_present']}")
    print(f"  Added as PENDING:          {stats['added']}  ({stats['borderline']} borderline)")
    print(f"  Filtered out (irrelevant): {stats['filtered_out']}")
    print(f"  Final log size:            {stats['final_count']}")

    if stats["added_papers"]:
        print(f"\nAdded papers:")
        for title in stats["added_papers"]:
            print(f"  + {title}")

    if stats["filtered_papers"]:
        print(f"\nFiltered out (sample, first 10):")
        for p in stats["filtered_papers"][:10]:
            print(f"  ✗ {p['title']}")
            print(f"    Reason: {p['reason']}")

    print("\nYour existing decisions are preserved. New papers added as PENDING.")
    print(f"Original backed up automatically.\n")


if __name__ == "__main__":
    main()
