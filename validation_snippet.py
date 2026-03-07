"""
Validation Philosophy — add this inside the Insights tab (sport scientist view only).
Place beneath the Evidence Review section.
"""

def show_validation_philosophy():
    """Collapsible validation framework — sport scientist audience only."""
    
    with st.expander("📐 Model Validation Philosophy", expanded=False):
        st.markdown("""
### How We Know the Model is Working

**V1 (Current): Does it match coach intuition?**

WAIMS does not yet operate as a trained injury classifier — the Forecast tab produces 
a heuristic risk score, not a validated predictive model. This is intentional. Without 
a full season of real-team injury events, formal classification validation would 
overstate confidence.

The meaningful V1 validation question is simpler:

> *Does the readiness ranking surface the same athletes the coach was already watching?*

A score that consistently surprises coaching staff is a red flag. A score that confirms 
and explains what the coach already senses — with quantified evidence — builds trust and 
gets used.

**V1 method:**
- Spearman rank correlation between WAIMS daily ranking and coach informal assessment
- Target: coach agrees with top/bottom 3 flagged athletes on ≥ 70% of days
- Collected via post-morning-brief feedback, logged per session
""")

        st.markdown("---")
        
        st.markdown("""
### V2 Validation Upgrades *(when 1 full season of real data available)*

| Method | What it answers |
|---|---|
| Walk-forward time splits | Will it work next week? |
| Player-holdout (GroupKFold) | Will it work for a new signing? |
| PR-AUC + calibration | When it flags risk, is it right? |
| Precision@K (top 3/day) | Are we surfacing the right conversations? |
| Lead-time analysis | Are flags arriving 3–7 days before injury? |
| Ablation studies | Which data streams are actually driving signal? |

**Baselines the model must beat:**
- Acute load threshold rule (last 7 days)
- ACWR heuristic alone  
- Player rolling z-score on soreness/fatigue

**Scope note:** Non-contact, load-related soft tissue injuries are the primary target. 
Contact injuries are not expected to validate — this is documented explicitly so 
staff understand model boundaries.
""")

        st.caption(
            "Validation framework informed by Julius.ai model validation analysis (2026). "
            "Applied and adapted for WAIMS operational context."
        )
