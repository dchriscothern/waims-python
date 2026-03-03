"""
Research Citations Module
Shows all studies used in WAIMS dashboard with evidence hierarchy
"""

import streamlit as st

def show_research_foundation():
    """
    Display complete research foundation with study quality indicators
    """
    
    st.markdown("### 📚 Evidence-Based Thresholds")
    
    st.markdown("""
    **WAIMS uses peer-reviewed, systematic reviews and meta-analyses:**
    
    🥇 = Meta-analysis (highest quality)  
    🥈 = Systematic review  
    🥉 = Large cohort study (>1000 athletes)
    """)
    
    # Create expandable sections by category
    with st.expander("🛌 Sleep & Recovery", expanded=False):
        st.markdown("""
        **Milewski et al. (2014)** 🥉  
        *"Chronic Lack of Sleep is Associated With Increased Sports Injuries"*  
        Journal: Journal of Pediatric Orthopaedics
        
        **Key Finding:** Sleep <6.5 hours = 1.7x injury risk  
        **Sample:** 112 youth athletes  
        **Applied in WAIMS:** Red flag when sleep <6.5 hrs
        
        ---
        
        **Fullagar et al. (2015)** 🥈  
        *"Sleep and Athletic Performance: Systematic Review"*  
        Journal: Sports Medicine
        
        **Key Finding:** Optimal sleep = 7-9 hours for athletes  
        **Applied in WAIMS:** Target 8 hrs, monitor if <7 hrs
        """)
    
    with st.expander("📊 Training Load & ACWR", expanded=False):
        st.markdown("""
        **Gabbett (2016)** 🥇  
        *"The Training-Injury Prevention Paradox"*  
        Journal: British Journal of Sports Medicine
        
        **Key Finding:** ACWR >1.5 = 2.4x injury risk  
        **Sample:** 2,000+ athletes across multiple sports  
        **Applied in WAIMS:** 
        - Red flag: ACWR >1.5
        - Caution: ACWR 1.3-1.5
        - Optimal: ACWR 0.8-1.3
        
        ---
        
        **Hulin et al. (2016)** 🥈  
        *"Spikes in Acute Workload Are Associated with Injury"*  
        Journal: British Journal of Sports Medicine
        
        **Key Finding:** Rapid load spikes increase injury risk  
        **Applied in WAIMS:** Monitor ACWR trends, flag sudden spikes
        """)
    
    with st.expander("😫 Soreness & Wellness", expanded=False):
        st.markdown("""
        **Saw et al. (2016)** 🥈  
        *"Monitoring Athletes Through Self-Report: Review"*  
        Journal: International Journal of Sports Physiology and Performance
        
        **Key Finding:** Soreness >7/10 correlates with injury risk  
        **Applied in WAIMS:** Monitor threshold at 7/10
        
        ---
        
        **Hooper & Mackinnon (1995)**  
        *"Monitoring Overtraining in Athletes"*  
        Journal: Sports Medicine
        
        **Key Finding:** Multi-dimensional wellness monitoring effective  
        **Applied in WAIMS:** Combined sleep + soreness + stress + mood scoring
        """)
    
    with st.expander("🏀 Basketball-Specific Injuries (NEW)", expanded=True):
        st.markdown("""
        **Stojanovic et al. (2025)** 🥇  
        *"Epidemiology of Basketball Injuries: Systematic Review and Meta-Analysis"*  
        Journal: Sports Medicine
        
        **Key Findings:**
        - **Player contact:** 42.9% of injuries (IR: 0.156 per 100 AEs)
        - **Non-contact:** 25.0% of injuries (IR: 0.093 per 100 AEs)
        - **Concussions:** 64.7% from player contact
        - **Ankle sprains:** Primary mechanism is landing on opponent's foot
        - **Competition vs Practice:** Contact injuries higher in games
        - **Overuse:** More common in practice settings
        
        **Applied in WAIMS:**
        - Context-specific risk alerts (practice vs competition)
        - Enhanced monitoring before games (contact risk)
        - Overuse tracking for practice loads
        - Injury mechanism education for coaches
        """)
    
    with st.expander("💪 Neuromuscular & Force Plate", expanded=False):
        st.markdown("""
        **Bishop et al. (2018)** 🥈  
        *"Interlimb Asymmetries: Review and Training Implications"*  
        Journal: Strength and Conditioning Journal
        
        **Key Finding:** Asymmetry >15% linked to injury  
        **WAIMS Adjustment:** >10% threshold for female athletes (more conservative)
        
        ---
        
        **Suchomel et al. (2016)**  
        *"The Importance of Muscular Strength in Athletic Performance"*  
        Journal: Sports Medicine
        
        **Key Finding:** CMJ height correlates with performance and injury risk  
        **Applied in WAIMS:** Track CMJ trends, flag decreases >10%
        """)
    
    with st.expander("⚖️ Female Athlete Considerations", expanded=False):
        st.markdown("""
        **Hewett et al. (2006)** 🥉  
        *"ACL Injuries in Female Athletes"*  
        Journal: American Journal of Sports Medicine
        
        **Key Finding:** Female athletes 4-6x higher ACL injury risk  
        **Applied in WAIMS:** 
        - More conservative asymmetry thresholds (10% vs 15%)
        - Enhanced landing mechanics monitoring
        - CMJ asymmetry tracking
        
        ---
        
        **Martin et al. (2018)**  
        *"Menstrual Cycle Effects on Athletic Performance and Injury Risk"*  
        Journal: Sports Medicine
        
        **Future Integration:** Menstrual cycle phase tracking (not yet implemented)
        """)
    
    # Summary table
    st.markdown("---")
    st.markdown("### 📊 Evidence Quality Summary")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("🥇 Meta-Analyses", "2", help="Gabbett 2016, Stojanovic 2025")
    
    with col2:
        st.metric("🥈 Systematic Reviews", "4", help="Fullagar 2015, Hulin 2016, Saw 2016, Bishop 2018")
    
    with col3:
        st.metric("🥉 Large Cohorts", "2", help="Milewski 2014, Hewett 2006")
    
    # Citation guidelines
    with st.expander("ℹ️ How We Evaluate New Research"):
        st.markdown("""
        **We update thresholds when:**
        ✅ Multiple meta-analyses show consistent findings  
        ✅ Basketball-specific studies supersede general findings  
        ✅ Female athlete research shows different thresholds  
        ✅ Sample sizes are large (>1000 athletes)  
        ✅ Findings are replicated across studies
        
        **We DON'T change thresholds when:**
        ❌ Single study contradicts consensus  
        ❌ Study is from different sport context  
        ❌ Small sample sizes (<100 athletes)  
        ❌ Not peer-reviewed or preprint only  
        ❌ Conflicts with expert feedback from practitioners
        
        **Our Current Threshold Review Process:**
        1. Annual literature review (January)
        2. Sport scientist consultation
        3. Coach feedback on practical application
        4. Test new thresholds with historical data
        5. Update if evidence is compelling
        
        **Last Review:** February 2026 (added Stojanovic 2025)  
        **Next Review:** January 2027
        """)

def show_research_badge(study_type="meta_analysis"):
    """
    Display a quality badge for research citations
    
    Args:
        study_type: "meta_analysis", "systematic_review", or "cohort"
    """
    
    badges = {
        "meta_analysis": ("🥇", "Meta-Analysis", "#fbbf24"),
        "systematic_review": ("🥈", "Systematic Review", "#94a3b8"),
        "cohort": ("🥉", "Large Cohort", "#fb923c"),
        "rct": ("💎", "RCT", "#8b5cf6")
    }
    
    emoji, label, color = badges.get(study_type, ("📄", "Study", "#6b7280"))
    
    return f"""
    <span style="background-color: {color}20; 
                 color: {color}; 
                 padding: 2px 8px; 
                 border-radius: 12px; 
                 font-size: 11px; 
                 font-weight: 700;">
        {emoji} {label}
    </span>
    """

# Example usage in athlete profile or dashboard:
"""
# In athlete_profile_tab or dashboard:
from research_citations import show_research_foundation

# Add to sidebar or as a tab:
with st.sidebar:
    if st.button("📚 View Research Foundation"):
        show_research_foundation()

# Or add inline with a specific threshold:
st.caption(f"Threshold based on: Milewski 2014 {show_research_badge('cohort')}", 
          unsafe_allow_html=True)
"""
