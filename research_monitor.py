"""
WAIMS Evidence Review System
=============================
Automated monitoring of new sports science research relevant to WAIMS thresholds,
signals, and methodology. Combines PubMed primary literature with expert practitioner
RSS feeds.

FORMAL EVIDENCE REVIEW POLICY (Orlando Magic-style)
----------------------------------------------------
No threshold or weighting change in WAIMS without a supporting meta-analysis or
systematic review. Single new studies go to WATCHLIST, not production.

Purpose: FORWARD-LOOKING INBOX only.
  Foundational papers (Walsh 2021, Gabbett 2016, Gathercole 2015, etc.) are already
  integrated in RESEARCH_FOUNDATION.md. This monitor surfaces NEW research only.
  Run weekly via GitHub Actions. Triage in Evidence Review tab (Insights).

Decision ladder:
  WATCHLIST  -> interesting, single study, monitor for replication
  CANDIDATE  -> appears in meta-analysis/SR; schedule formal staff review
  APPROVED   -> reviewed by performance staff, approved for WAIMS update
  INTEGRATED -> change made to code, RESEARCH_FOUNDATION.md, README, roadmap
  REJECTED   -> reviewed, not applicable (wrong population, sport, etc.)

Usage:
  python research_monitor.py                          # last 7 days, console
  python research_monitor.py --days 30                # last 30 days
  python research_monitor.py --save                   # save/update research_log.json
  python research_monitor.py --html                   # HTML decision report
  python research_monitor.py --output custom.json     # save to different file
  python research_monitor.py --github-action          # print GitHub Actions YAML
"""

import urllib.request
import urllib.parse
import urllib.error
import json
import argparse
import time
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path


# ==============================================================================
# PUBMED SEARCH TOPICS (tightened -- sport science only, no clinical noise)
# Each query is narrowly targeted to avoid pulling in irrelevant medical papers.
# ==============================================================================
PUBMED_TOPICS = [
    {
        "topic": "Sleep & Athlete Injury Risk",
        "query": (
            '(sleep[Title/Abstract]) AND '
            '(athlete[Title/Abstract] OR "sport performance"[Title/Abstract] OR basketball[Title/Abstract]) AND '
            '(injury[Title/Abstract] OR recovery[Title/Abstract] OR readiness[Title/Abstract]) NOT '
            '(zolpidem OR pharmacol OR "clinical trial" OR insomnia[Title] OR cardiac OR cancer OR surgery)'
        ),
        "waims_signal": "sleep_hours threshold (<7h flag, <6h hard floor -- Walsh 2021)",
        "waims_action": "Would change <7h threshold or readiness formula sleep weight",
        "tags": ["sleep", "injury"],
    },
    {
        "topic": "CMJ / RSI as Fatigue Marker",
        "query": (
            '("countermovement jump"[Title/Abstract] OR CMJ[Title/Abstract] OR '
            '"reactive strength index"[Title/Abstract] OR RSI[Title/Abstract]) AND '
            '(fatigue[Title/Abstract] OR monitoring[Title/Abstract] OR readiness[Title/Abstract] OR '
            'neuromuscular[Title/Abstract])'
        ),
        "waims_signal": "CMJ z-score and RSI z-score -- primary objective signals",
        "waims_action": "Would change primary signal weights or z-score thresholds",
        "tags": ["force_plate", "neuromuscular"],
    },
    {
        "topic": "Basketball Load Monitoring",
        "query": (
            '(basketball[Title/Abstract] OR WNBA[Title/Abstract]) AND '
            '("training load"[Title/Abstract] OR "player load"[Title/Abstract] OR '
            'readiness[Title/Abstract] OR fatigue[Title/Abstract] OR monitoring[Title/Abstract])'
        ),
        "waims_signal": "All signals -- basketball-specific context and baselines",
        "waims_action": "Direct application, especially female basketball and positional norms",
        "tags": ["basketball", "load"],
    },
    {
        "topic": "Female Athlete Monitoring & Recovery",
        "query": (
            '("female athlete"[Title/Abstract] OR "women\'s basketball"[Title/Abstract] OR '
            '"female basketball"[Title/Abstract]) AND '
            '(load[Title/Abstract] OR monitoring[Title/Abstract] OR recovery[Title/Abstract] OR '
            'readiness[Title/Abstract] OR injury[Title/Abstract] OR fatigue[Title/Abstract])'
        ),
        "waims_signal": "Female-specific thresholds -- core WAIMS design principle",
        "waims_action": "Would change female-specific recovery rates or CMJ baselines",
        "tags": ["female", "recovery"],
    },
    {
        "topic": "Deceleration Monitoring",
        "query": (
            '(deceleration[Title/Abstract] OR "high-speed deceleration"[Title/Abstract]) AND '
            '(injury[Title/Abstract] OR monitoring[Title/Abstract] OR GPS[Title/Abstract] OR '
            'basketball[Title/Abstract] OR "team sport"[Title/Abstract]) AND '
            '(athlete[Title/Abstract] OR sport[Title/Abstract])'
        ),
        "waims_signal": "decel_count z-score -- primary GPS injury-risk signal",
        "waims_action": "Would change how decel count is interpreted or thresholded",
        "tags": ["decel", "GPS"],
    },
    {
        "topic": "GPS Load Monitoring",
        "query": (
            '(GPS[Title/Abstract] OR "player load"[Title/Abstract] OR accelerometer[Title/Abstract]) AND '
            '(basketball[Title/Abstract] OR "team sport"[Title/Abstract]) AND '
            '(monitoring[Title/Abstract] OR load[Title/Abstract] OR validity[Title/Abstract])'
        ),
        "waims_signal": "GPS framing -- external load only (Boskovic 2024 GPS 3.0)",
        "waims_action": "Would update GPS signal weighting or framing",
        "tags": ["GPS", "load"],
    },
    {
        "topic": "ACWR Methodology",
        "query": (
            '("acute chronic workload ratio"[Title/Abstract] OR ACWR[Title/Abstract] OR '
            '"acute:chronic"[Title/Abstract]) AND '
            '(injury[Title/Abstract] OR validity[Title/Abstract] OR methodology[Title/Abstract]) AND '
            '(athlete[Title/Abstract] OR sport[Title/Abstract])'
        ),
        "waims_signal": "ACWR -- contextual flag only (Impellizzeri 2020)",
        "waims_action": "Evidence for ACWR rehabilitation or further critique",
        "tags": ["ACWR"],
    },
    {
        "topic": "Menstrual Cycle & Athletic Performance",
        "query": (
            '("menstrual cycle"[Title/Abstract] OR "luteal phase"[Title/Abstract]) AND '
            '("athletic performance"[Title/Abstract] OR "injury risk"[Title/Abstract] OR '
            '"neuromuscular"[Title/Abstract] OR ACL[Title/Abstract] OR recovery[Title/Abstract]) AND '
            '(athlete[Title/Abstract] OR sport[Title/Abstract] OR exercise[Title/Abstract])'
        ),
        "waims_signal": "V2 feature -- menstrual cycle phase adjustment",
        "waims_action": "Evidence base for future menstrual cycle integration (V2 roadmap)",
        "tags": ["female", "hormonal", "V2"],
    },
    {
        "topic": "Basketball Injury Epidemiology",
        "query": (
            '(basketball[Title/Abstract] OR WNBA[Title/Abstract]) AND '
            '("systematic review"[Title/Abstract] OR "meta-analysis"[Title/Abstract]) AND '
            '(injur[Title/Abstract] OR ACL[Title/Abstract] OR ankle[Title/Abstract] OR knee[Title/Abstract])'
        ),
        "waims_signal": "Basketball-specific risk context section",
        "waims_action": "Would update injury mechanism language in risk context",
        "tags": ["basketball", "injury"],
    },
    {
        "topic": "Travel & Circadian Load",
        "query": (
            '(travel[Title/Abstract] OR "time zone"[Title/Abstract] OR circadian[Title/Abstract]) AND '
            '(athlete[Title/Abstract] OR basketball[Title/Abstract] OR NBA[Title/Abstract]) AND '
            '(performance[Title/Abstract] OR fatigue[Title/Abstract] OR sleep[Title/Abstract])'
        ),
        "waims_signal": "B2B + travel scenario -- eastward vs westward penalty (V2)",
        "waims_action": "Would update circadian/travel penalty in load projection",
        "tags": ["travel", "circadian", "sleep"],
    },
]


# ==============================================================================
# POST-FETCH RELEVANCE FILTER
# Applied after PubMed returns results to catch any clinical noise
# ==============================================================================

# Title must contain at least one sport-relevant term
TITLE_INCLUDE_TERMS = [
    "athlete", "sport", "basketball", "player", "training", "exercise",
    "physical", "performance", "fitness", "load", "fatigue", "recovery",
    "sleep", "jump", "gps", "monitoring", "readiness", "injury",
    "female", "women", "wnba", "nba", "neuromuscular", "deceleration",
    "acwr", "workload",
]

# Paper is rejected if title contains any of these clinical terms
TITLE_EXCLUDE_TERMS = [
    "surgery", "surgical", "operative", "pharmacol", "drug trial",
    "placebo", "biopsy", "histolog", "patholog", "radiology",
    "cancer", "tumor", "oncol", "cardiac arrest", "sepsis",
    "inpatient", "anesthesia", "post-operative", "preoperative",
    "gastroesophageal", "reflux", "kidney", "liver", "hepat",
    "ophthalmol", "retinal", "myocardial", "arrhythmia",
    "guinea pig", "equine", "rodent", "mouse", "bovine",
    "intimate partner", "endometrial", "ovarian", "polycystic",
    "embryo", "ivf", "luteal stimulation", "follicular stimulation",
    "tinnitus", "migraine", "depression medication", "psychiatr",
]


def passes_relevance_filter(title: str) -> bool:
    """Returns True if paper should be included, False if it should be discarded."""
    t = title.lower()
    # Hard exclude
    for term in TITLE_EXCLUDE_TERMS:
        if term in t:
            return False
    # Must include at least one sport term
    for term in TITLE_INCLUDE_TERMS:
        if term in t:
            return True
    return False


# ==============================================================================
# EXPERT RSS SOURCES
# ==============================================================================
RSS_SOURCES = [
    {
        "name": "Martin Buchheit",
        "url": "https://martin-buchheit.net/feed/",
        "type": "expert_practitioner",
        "trust_level": "HIGH",
        "subscription_required": False,
    },
    {
        "name": "SPSR (Sport Performance & Science Reports)",
        "url": "https://sportperfsci.com/feed/",
        "type": "practitioner_journal",
        "trust_level": "HIGH",
        "subscription_required": False,
    },
    {
        "name": "BJSM Blog",
        "url": "https://blogs.bmj.com/bjsm/feed/",
        "type": "journal_blog",
        "trust_level": "HIGH",
        "subscription_required": False,
    },
    {
        "name": "Sportsmith",
        "url": None,
        "type": "applied_practice",
        "trust_level": "HIGH",
        "subscription_required": True,
        "manual_note": "MANUAL ONLY -- $13/month. Read weekly. Log as 'Source: Sportsmith (manual YYYY-MM-DD)'.",
    },
]


# ==============================================================================
# QUALITY SCORING
# ==============================================================================
QUALITY_KEYWORDS = {
    "meta-analysis":     {"score": 10, "label": "META-ANALYSIS"},
    "systematic review": {"score": 9,  "label": "SYSTEMATIC REVIEW"},
    "randomised":        {"score": 7,  "label": "RCT"},
    "randomized":        {"score": 7,  "label": "RCT"},
    "prospective":       {"score": 6,  "label": "PROSPECTIVE"},
    "cohort":            {"score": 5,  "label": "COHORT"},
    "basketball":        {"score": 3,  "label": "BASKETBALL"},
    "wnba":              {"score": 4,  "label": "WNBA"},
    "female":            {"score": 2,  "label": "FEMALE"},
    "women":             {"score": 2,  "label": "FEMALE"},
    "review":            {"score": 1,  "label": "REVIEW"},
}

PUBMED_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
RATE_SLEEP  = 0.4


# ==============================================================================
# PUBMED
# ==============================================================================
def search_pubmed(query, days):
    params = urllib.parse.urlencode({
        "db": "pubmed", "term": query, "retmax": 25,
        "sort": "pub+date", "retmode": "json",
        "datetype": "pdat", "reldate": days,
    })
    try:
        req = urllib.request.urlopen(PUBMED_BASE + "esearch.fcgi?" + params, timeout=15)
        return json.loads(req.read())["esearchresult"].get("idlist", [])
    except Exception as e:
        print(f"    PubMed search error: {e}")
        return []


def fetch_summaries(pmids):
    if not pmids:
        return {}
    params = urllib.parse.urlencode({"db": "pubmed", "id": ",".join(pmids), "retmode": "json"})
    try:
        req = urllib.request.urlopen(PUBMED_BASE + "esummary.fcgi?" + params, timeout=15)
        return json.loads(req.read()).get("result", {})
    except Exception as e:
        print(f"    PubMed fetch error: {e}")
        return {}


def score_paper(title):
    text = title.lower()
    score, labels, seen = 0, [], set()
    for kw, meta in QUALITY_KEYWORDS.items():
        if kw in text and meta["label"] not in seen:
            score += meta["score"]
            labels.append(meta["label"])
            seen.add(meta["label"])
    return score, labels


# ==============================================================================
# RSS
# ==============================================================================
def fetch_rss(source, days):
    if not source.get("url"):
        return []
    cutoff = datetime.now() - timedelta(days=days)
    items  = []
    try:
        req  = urllib.request.Request(source["url"], headers={"User-Agent": "WAIMS-ResearchMonitor/1.0"})
        resp = urllib.request.urlopen(req, timeout=15)
        root = ET.fromstring(resp.read())
        ns   = {"atom": "http://www.w3.org/2005/Atom"}
        entries = root.findall(".//item") or root.findall(".//atom:entry", ns)
        for entry in entries:
            title    = (entry.findtext("title") or "").strip()
            link     = (entry.findtext("link")  or "").strip()
            date_str = entry.findtext("pubDate") or entry.findtext("atom:published", ns) or ""
            desc     = re.sub(r'<[^>]+>', ' ', entry.findtext("description") or "").strip()[:300]
            pub_date = None
            for fmt in ["%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z",
                        "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"]:
                try:
                    pub_date = datetime.strptime(date_str.strip()[:30], fmt).replace(tzinfo=None)
                    break
                except Exception:
                    continue
            if pub_date and pub_date < cutoff:
                continue
            score, labels = score_paper(title)
            items.append({
                "id": f"rss_{re.sub(r'[^a-z0-9]','_',title.lower())[:40]}",
                "source": source["name"], "source_type": source["type"],
                "trust_level": source["trust_level"],
                "title": title, "url": link,
                "pub_date": pub_date.strftime("%Y-%m-%d") if pub_date else "Unknown",
                "excerpt": desc, "quality_score": score, "quality_labels": labels,
                "waims_signal": "Practitioner article -- assess manually",
                "waims_action": "Does this change a threshold or interpretation? Cross-check with Sportsmith.",
                "decision": "PENDING",
            })
    except Exception as e:
        print(f"    RSS error ({source['name']}): {e}")
    return items


# ==============================================================================
# EVIDENCE GATE
# ==============================================================================
def apply_gate(papers):
    for p in papers:
        labels      = p.get("quality_labels", [])
        source_type = p.get("source_type", "pubmed")
        score       = p.get("quality_score", 0)

        if source_type in ("expert_practitioner", "practitioner_journal", "journal_blog"):
            p["gate_status"] = "ASSESS"
            p["gate_note"]   = ("Practitioner article -- assess against real-world context. "
                                "Does it align with or contradict your Sportsmith reading this week?")
        elif "META-ANALYSIS" in labels or "SYSTEMATIC REVIEW" in labels:
            p["gate_status"] = "CANDIDATE"
            p["gate_note"]   = ("ELIGIBLE FOR THRESHOLD REVIEW. Check: same population? Same sport/sex? "
                                "Meaningful effect size? If yes -- schedule formal review with performance staff.")
        elif "BASKETBALL" in labels or "WNBA" in labels:
            p["gate_status"] = "REVIEW"
            p["gate_note"]   = ("Basketball-specific -- read abstract carefully. "
                                "Single study: WATCHLIST only. Do not change thresholds alone.")
        elif score >= 6:
            p["gate_status"] = "WATCHLIST"
            p["gate_note"]   = ("Prospective or cohort study. Monitor for replication. "
                                "Escalate to CANDIDATE if confirmed in future meta-analysis.")
        else:
            p["gate_status"] = "BACKGROUND"
            p["gate_note"]   = "Background awareness only. Not sufficient basis for threshold change."
    return papers


# ==============================================================================
# SAVE LOG
# ==============================================================================
def save_log(new_items, output_path="research_log.json"):
    log_path = Path(output_path)
    existing = []
    if log_path.exists():
        try:
            existing = json.loads(log_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    existing_ids = {p.get("id") or p.get("pmid") or p.get("url", "") for p in existing}
    to_add = []
    for p in new_items:
        pid = p.get("id") or p.get("pmid") or p.get("url", "")
        if pid not in existing_ids:
            p["date_found"]     = datetime.now().strftime("%Y-%m-%d")
            p["decision"]       = "PENDING"
            p["decision_by"]    = ""
            p["decision_date"]  = ""
            p["decision_notes"] = ""
            to_add.append(p)
    combined = to_add + existing
    log_path.write_text(json.dumps(combined, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Saved {len(to_add)} new items to {output_path} (total: {len(combined)})\n")


# ==============================================================================
# HTML REPORT
# ==============================================================================
def generate_html(pubmed_papers, rss_items, days):
    date_str = datetime.now().strftime("%B %d, %Y")
    fname    = f"research_report_{datetime.now().strftime('%Y%m%d')}.html"

    GATE_CFG = {
        "CANDIDATE":  ("#dc2626", "CANDIDATE -- eligible for threshold review"),
        "REVIEW":     ("#d97706", "REVIEW -- read carefully"),
        "WATCHLIST":  ("#64748b", "WATCHLIST -- single study, monitor"),
        "BACKGROUND": ("#94a3b8", "BACKGROUND -- awareness only"),
        "ASSESS":     ("#0284c7", "ASSESS -- practitioner article"),
    }
    LABEL_COLORS = {
        "META-ANALYSIS":"#7c3aed","SYSTEMATIC REVIEW":"#1d4ed8",
        "RCT":"#0369a1","PROSPECTIVE":"#0891b2","COHORT":"#0e7490",
        "BASKETBALL":"#ca8a04","WNBA":"#b45309","FEMALE":"#be185d","REVIEW":"#64748b",
    }

    def badge(status):
        c, t = GATE_CFG.get(status, ("#94a3b8", status))
        return f'<span style="background:{c};color:white;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:700;">{t}</span>'

    def qlabels(labels):
        return "".join(
            f'<span style="background:{LABEL_COLORS.get(l,"#64748b")};color:white;'
            f'padding:1px 6px;border-radius:3px;font-size:10px;font-weight:600;margin-right:3px;">{l}</span>'
            for l in labels)

    def card(p):
        bc   = GATE_CFG.get(p["gate_status"], ("#94a3b8", ""))[0]
        doi  = (f'<a href="https://doi.org/{p["doi"]}" style="color:#0284c7;font-size:12px;">DOI</a> | '
                if p.get("doi") else "")
        excpt = (f'<div style="font-size:11px;color:#475569;margin-bottom:6px;font-style:italic;">{p.get("excerpt","")[:200]}</div>'
                 if p.get("excerpt") else "")
        src  = p.get("authors", "") or p.get("source", "")
        jrn  = p.get("journal", "") or ""
        return f"""
<div style="border:1px solid #e2e8f0;border-left:4px solid {bc};border-radius:0 8px 8px 0;
     padding:16px;margin-bottom:12px;background:white;">
  <div style="margin-bottom:8px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:4px;">
    <div>{badge(p['gate_status'])} &nbsp; {qlabels(p.get('quality_labels',[]))}</div>
    <div style="font-size:11px;color:#94a3b8;">{p.get('pub_date','?')}</div>
  </div>
  <div style="font-size:14px;font-weight:600;color:#0f172a;margin-bottom:4px;line-height:1.4;word-wrap:break-word;">{p['title']}</div>
  <div style="font-size:12px;color:#475569;margin-bottom:4px;">{src}{' | ' if src and jrn else ''}<em>{jrn}</em></div>
  {excpt}
  <div style="background:#f0f9ff;border-radius:4px;padding:5px 10px;font-size:11px;color:#0369a1;margin-bottom:6px;">
    <b>WAIMS:</b> {p.get('waims_signal','')}
  </div>
  <div style="background:#fefce8;border-radius:4px;padding:5px 10px;font-size:11px;color:#713f12;margin-bottom:8px;">
    <b>Gate:</b> {p.get('gate_note','')}
  </div>
  <div style="font-size:12px;">
    {doi}<a href="{p.get('url','#')}" target="_blank" style="color:#0284c7;">View</a>
  </div>
</div>"""

    groups = [
        ("CANDIDATES -- Eligible for threshold review",     [p for p in pubmed_papers if p["gate_status"] == "CANDIDATE"]),
        ("REVIEW -- Basketball-specific / high-relevance",  [p for p in pubmed_papers if p["gate_status"] == "REVIEW"]),
        ("PRACTITIONER ARTICLES -- Expert RSS feeds",       rss_items),
        ("WATCHLIST -- Single studies, monitor",            [p for p in pubmed_papers if p["gate_status"] == "WATCHLIST"]),
        ("BACKGROUND -- Awareness only",                    [p for p in pubmed_papers if p["gate_status"] == "BACKGROUND"]),
    ]
    body = ""
    for heading, items in groups:
        if not items:
            continue
        body += f'<h2 style="color:#1e3a5f;border-bottom:2px solid #e2e8f0;padding-bottom:8px;">{heading} ({len(items)})</h2>\n'
        body += "\n".join(card(p) for p in items)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>WAIMS Evidence Review — {date_str}</title>
  <style>body{{font-family:Arial,sans-serif;max-width:960px;margin:40px auto;padding:0 24px;background:#f8fafc;}}</style>
</head>
<body>
  <div style="background:#1e3a5f;color:white;border-radius:8px;padding:20px 28px;margin-bottom:20px;">
    <div style="font-size:22px;font-weight:700;">WAIMS Evidence Review System</div>
    <div style="margin-top:6px;opacity:.85;">{date_str} | Last {days} days |
    {len(pubmed_papers)} PubMed | {len(rss_items)} practitioner articles</div>
  </div>
  <div style="background:#fef3c7;border-left:4px solid #d97706;border-radius:0 8px 8px 0;padding:12px 16px;margin-bottom:16px;font-size:13px;">
    <b>Purpose:</b> Forward-looking inbox only. Foundational papers are in RESEARCH_FOUNDATION.md.
    This tab surfaces NEW research for weekly triage. No threshold change without meta-analysis support.
  </div>
  {body}
  <p style="text-align:center;color:#94a3b8;font-size:12px;margin-top:40px;">
    WAIMS Evidence Review -- PubMed E-utilities + public RSS feeds
  </p>
</body>
</html>"""

    Path(fname).write_text(html, encoding='utf-8')
    print(f"  HTML report: {fname}\n")


# ==============================================================================
# GITHUB ACTIONS YAML
# ==============================================================================
GITHUB_YAML = """\
# .github/workflows/research_monitor.yml
name: WAIMS Evidence Review
on:
  schedule:
    - cron: '0 8 * * 1'
  workflow_dispatch:

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.12'}
      - run: python research_monitor.py --days 7 --save --html
      - name: Commit results
        run: |
          git config user.name "WAIMS Evidence Monitor"
          git config user.email "monitor@waims"
          git add research_log.json research_report_*.html 2>/dev/null || true
          git diff --staged --quiet || git commit -m "Evidence review $(date +%Y-%m-%d)"
          git push
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
"""


# ==============================================================================
# MAIN
# ==============================================================================
def run_monitor(days=7, save=False, html=False, output_path="research_log.json"):
    print(f"\n{'='*60}")
    print(f"  WAIMS Evidence Review -- last {days} days (new research only)")
    print(f"  {datetime.now().strftime('%B %d, %Y  %H:%M')}")
    print(f"{'='*60}\n")

    all_papers = {}

    print("── PubMed ───────────────────────────────────────────────────\n")
    for cfg in PUBMED_TOPICS:
        print(f"  {cfg['topic']}...")
        pmids = search_pubmed(cfg["query"], days)
        time.sleep(RATE_SLEEP)
        if not pmids:
            print("    No new papers.\n"); continue
        summaries = fetch_summaries(pmids)
        time.sleep(RATE_SLEEP)
        new = 0
        for pmid in pmids:
            if pmid in all_papers:
                all_papers[pmid]["topics"].append(cfg["topic"]); continue
            art = summaries.get(pmid, {})
            if not art or not art.get("title"): continue

            # Apply relevance filter -- skip clinical noise
            if not passes_relevance_filter(art.get("title", "")):
                continue

            authors = art.get("authors", [])
            doi     = next((u["value"] for u in art.get("articleids", []) if u["idtype"] == "doi"), None)
            score, labels = score_paper(art.get("title", ""))
            all_papers[pmid] = {
                "id": f"pmid_{pmid}", "pmid": pmid,
                "source": "PubMed", "source_type": "pubmed", "trust_level": "PRIMARY",
                "title": art.get("title", "Unknown"),
                "authors": (authors[0].get("name", "?") + " et al.") if authors else "Unknown",
                "journal": art.get("source", "Unknown"),
                "pub_date": art.get("pubdate", "?"),
                "doi": doi, "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "topics": [cfg["topic"]],
                "waims_signal": cfg["waims_signal"],
                "waims_action": cfg["waims_action"],
                "tags": cfg["tags"],
                "quality_score": score, "quality_labels": labels,
                "decision": "PENDING",
            }
            new += 1
        print(f"    {new} new (total unique after filter: {len(all_papers)})\n")

    print("── Expert RSS feeds ─────────────────────────────────────────\n")
    rss_items = []
    for src in RSS_SOURCES:
        if src.get("subscription_required"):
            print(f"  {src['name']}: MANUAL -- {src.get('manual_note','')}\n"); continue
        print(f"  {src['name']}...")
        items = fetch_rss(src, days)
        rss_items.extend(items)
        print(f"    {len(items)} articles\n")
        time.sleep(0.5)

    pubmed_list = apply_gate(list(all_papers.values()))
    rss_items   = apply_gate(rss_items)
    pubmed_list.sort(key=lambda x: x["quality_score"], reverse=True)

    candidates = [p for p in pubmed_list if p["gate_status"] == "CANDIDATE"]
    reviews    = [p for p in pubmed_list if p["gate_status"] == "REVIEW"]
    watchlist  = [p for p in pubmed_list if p["gate_status"] == "WATCHLIST"]

    def pr(p):
        print(f"  [{p['gate_status']}] Score {p['quality_score']} | {' . '.join(p.get('quality_labels',[]))}")
        print(f"  {p['title'][:90]}{'...' if len(p['title'])>90 else ''}")
        print(f"  {p.get('authors','')} | {p.get('journal','')} | {p.get('pub_date','')}")
        print(f"  Signal: {p['waims_signal']}")
        print(f"  Gate:   {p['gate_note']}")
        print(f"  URL:    {p['url']}\n")

    print(f"\n{'='*60}  RESULTS\n")
    if candidates:
        print(f"CANDIDATES ({len(candidates)}) -- eligible for threshold review\n")
        for p in candidates: pr(p)
    if reviews:
        print(f"REVIEW ({len(reviews)}) -- basketball-specific\n")
        for p in reviews[:6]: pr(p)
    if watchlist:
        print(f"WATCHLIST ({len(watchlist)}) -- single studies\n")
        for p in watchlist[:4]: pr(p)
        if len(watchlist) > 4: print(f"  ... +{len(watchlist)-4} more\n")
    if rss_items:
        print(f"PRACTITIONER ({len(rss_items)}) -- expert RSS\n")
        for p in rss_items[:5]:
            print(f"  [{p['source']}] {p['pub_date']} -- {p['title'][:80]}")
            print(f"  {p['url']}\n")

    print(f"{'─'*60}")
    print("  SPORTSMITH: https://www.sportsmith.co/learn/ -- manual weekly review")
    print(f"{'─'*60}\n")
    print("  POLICY: No threshold change without meta-analysis support.")
    print("  CANDIDATE -> staff review -> APPROVED -> code + docs update\n")

    all_items = pubmed_list + rss_items
    if save: save_log(all_items, output_path)
    if html: generate_html(pubmed_list, rss_items, days)
    return all_items


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WAIMS Evidence Review System")
    parser.add_argument("--days",          type=int, default=7)
    parser.add_argument("--save",          action="store_true")
    parser.add_argument("--html",          action="store_true")
    parser.add_argument("--output",        type=str, default="research_log.json",
                        help="Output path for research log (default: research_log.json)")
    parser.add_argument("--github-action", action="store_true")
    args = parser.parse_args()
    if args.github_action:
        print(GITHUB_YAML)
    else:
        run_monitor(days=args.days, save=args.save, html=args.html, output_path=args.output)
