"""
Research Context Module
Adds evidence-based basketball injury insights to dashboard
Based on: Stojanovic et al. (2025) - Epidemiology of Basketball Injuries
"""

import streamlit as st
import plotly.graph_objects as go

def basketball_injury_research_panel():
    """
    Display research-backed injury insights for basketball
    Citation: Stojanovic E, et al. Sports Med. 2025
    """
    
    with st.expander("📚 Basketball Injury Research Insights", expanded=False):
        st.markdown("### Evidence-Based Injury Prevention")
        st.caption("Source: Stojanovic E, et al. Sports Med. 2025 - Systematic Review & Meta-Analysis")
        
        # Create tabs for different research aspects
        tab1, tab2, tab3 = st.tabs(["Injury Mechanisms", "Risk Factors", "Prevention Strategies"])
        
        with tab1:
            st.markdown("#### Primary Injury Mechanisms in Basketball")
            
            # Mechanism breakdown chart
            mechanisms = {
                'Player Contact': 42.9,
                'Non-Contact': 25.0,
                'Surface Contact': 16.0,
                'Equipment Contact': 16.1
            }
            
            fig = go.Figure(data=[go.Pie(
                labels=list(mechanisms.keys()),
                values=list(mechanisms.values()),
                hole=.3,
                marker_colors=['#ef4444', '#f59e0b', '#3b82f6', '#8b5cf6']
            )])
            
            fig.update_layout(
                title="Injury Mechanism Distribution",
                height=300,
                showlegend=True
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Detailed breakdown
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("""
                **🔴 Player Contact (42.9%)**
                - Most frequent mechanism
                - IR: 0.156 per 100 AEs
                - Primary cause of ankle sprains
                - 64.7% of concussions
                - Higher in competition vs practice
                
                **🟡 Non-Contact (25.0%)**
                - IR: 0.093 per 100 AEs
                - Results from rapid direction changes
                - High musculoskeletal loading
                - Jumping and landing injuries
                """)
            
            with col2:
                st.markdown("""
                **🔵 Surface Contact (16.0%)**
                - IR: 0.041 per 100 AEs
                - Falls and floor contact
                - 12.9% of concussions
                
                **🟣 Equipment Contact (16.1%)**
                - IR: 0.060 per 100 AEs
                - Ball, hoop, out-of-bounds objects
                - Combined mechanism category
                """)
        
        with tab2:
            st.markdown("#### Key Risk Factors")
            
            st.markdown("""
            **Competition vs Practice:**
            - Player contact injuries significantly higher in competition
            - Overuse injuries more common in practice settings
            
            **Level of Play:**
            - Player contact injuries more prevalent in collegiate vs high school
            - Overuse injuries significantly higher in collegiate players
            
            **Common Injury Patterns:**
            - **Ankle Sprains:** Often from landing on opponent's foot (player contact)
            - **Concussions:** 64.7% from player contact, 12.9% from surface contact
            - **Overuse Injuries:** Predominantly practice-related
            
            **Physical Demands:**
            - Rapid velocity changes
            - Frequent direction changes
            - High-frequency jumping and landing
            - Elevated musculoskeletal loading
            """)
        
        with tab3:
            st.markdown("#### Evidence-Based Prevention Strategies")
            
            st.info("""
            **Based on injury mechanism data, monitoring should focus on:**
            """)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("""
                **🎯 Priority Monitoring Areas:**
                
                1. **Contact Readiness (42.9% of injuries)**
                   - Physical conditioning
                   - Recovery status
                   - Neuromuscular fatigue
                   - Reaction time
                
                2. **Movement Quality (25% non-contact)**
                   - Landing mechanics
                   - Change of direction ability
                   - Jump-landing asymmetries
                   - Proprioception status
                
                3. **Fatigue Management**
                   - Practice vs game loads
                   - Overuse indicators
                   - Cumulative stress
                """)
            
            with col2:
                st.markdown("""
                **✅ Actionable Interventions:**
                
                **High Risk Indicators:**
                - Sleep <6.5 hrs + game day = ↑ contact injury risk
                - High soreness + intense practice = ↑ non-contact risk
                - Elevated ACWR >1.5 = ↑ overuse injury risk
                
                **Protective Factors:**
                - Adequate sleep (≥8 hrs)
                - Optimal load balance (ACWR 0.8-1.3)
                - Low soreness (<5/10)
                - Good neuromuscular function (CMJ/RSI)
                
                **Intervention Timing:**
                - Pre-competition: Ensure contact readiness
                - Pre-practice: Monitor overuse indicators
                - Post-training: Assess recovery needs
                """)

def injury_mechanism_insight_box(athlete_data, context="practice"):
    """
    Show context-specific injury risk based on research
    
    Args:
        athlete_data: Dict with sleep_hours, soreness, acwr
        context: "practice" or "competition"
    """
    
    sleep = athlete_data.get('sleep_hours', 7)
    soreness = athlete_data.get('soreness', 5)
    acwr = athlete_data.get('acwr', 1.0)
    
    # Calculate context-specific risk
    if context == "competition":
        # Player contact is most common (42.9%) and higher in competition
        if sleep < 6.5 or soreness > 7:
            risk_level = "🔴 Elevated"
            risk_color = "#fee2e2"
            message = """
            **Elevated Contact Injury Risk**
            - Player contact causes 42.9% of injuries (highest in competition)
            - Current readiness indicators suggest reduced reaction capacity
            - Consider modified playing time or additional warm-up
            """
        elif sleep < 7.5 or soreness > 5:
            risk_level = "🟡 Moderate"
            risk_color = "#fef3c7"
            message = """
            **Moderate Contact Risk**
            - Monitor closely during competition
            - Player contact injuries are most common mechanism
            - Ensure proper warm-up and taping/bracing if needed
            """
        else:
            risk_level = "🟢 Low"
            risk_color = "#d1fae5"
            message = """
            **Good Contact Readiness**
            - Readiness indicators support safe competition
            - Continue monitoring for signs of fatigue
            """
    
    else:  # practice
        # Overuse and non-contact more common in practice
        if acwr > 1.5 or soreness > 7:
            risk_level = "🔴 Elevated"
            risk_color = "#fee2e2"
            message = """
            **Elevated Overuse/Non-Contact Risk**
            - Overuse injuries more common in practice (especially collegiate)
            - Non-contact injuries (25%) often from rapid movements
            - Consider reduced intensity or volume today
            """
        elif acwr > 1.3 or soreness > 5:
            risk_level = "🟡 Moderate"
            risk_color = "#fef3c7"
            message = """
            **Moderate Practice Risk**
            - Monitor movement quality and fatigue
            - Non-contact injuries account for 25% of all injuries
            - Focus on controlled movements and proper mechanics
            """
        else:
            risk_level = "🟢 Low"
            risk_color = "#d1fae5"
            message = """
            **Good Practice Readiness**
            - Load and recovery indicators are optimal
            - Continue monitoring for cumulative fatigue
            """
    
    st.markdown(
        f"""
        <div style="background-color: {risk_color}; 
                    padding: 15px; 
                    border-radius: 8px; 
                    border-left: 4px solid {'#ef4444' if 'Elevated' in risk_level else '#f59e0b' if 'Moderate' in risk_level else '#10b981'};">
            <div style="font-weight: 700; margin-bottom: 8px; font-size: 16px;">
                {risk_level} - {context.title()} Context
            </div>
            <div style="font-size: 14px; line-height: 1.6;">
                {message}
            </div>
            <div style="margin-top: 10px; font-size: 12px; color: #6b7280;">
                <em>Based on: Stojanovic et al. (2025) - Basketball injury epidemiology</em>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

def quick_reference_card():
    """Quick reference card for injury mechanisms"""
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 20px;
                border-radius: 12px;
                color: white;
                margin: 20px 0;">
        <h3 style="margin: 0 0 15px 0; color: white;">🏀 Basketball Injury Quick Reference</h3>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
            <div style="background: rgba(255,255,255,0.1); padding: 12px; border-radius: 8px;">
                <div style="font-weight: 700; margin-bottom: 5px;">⚠️ Highest Risk:</div>
                <div style="font-size: 14px;">Player Contact (42.9%)</div>
                <div style="font-size: 12px; opacity: 0.9;">Most common in competition</div>
            </div>
            
            <div style="background: rgba(255,255,255,0.1); padding: 12px; border-radius: 8px;">
                <div style="font-weight: 700; margin-bottom: 5px;">🏃 Non-Contact:</div>
                <div style="font-size: 14px;">25% of injuries</div>
                <div style="font-size: 12px; opacity: 0.9;">From rapid movements</div>
            </div>
            
            <div style="background: rgba(255,255,255,0.1); padding: 12px; border-radius: 8px;">
                <div style="font-weight: 700; margin-bottom: 5px;">🧠 Concussions:</div>
                <div style="font-size: 14px;">64.7% player contact</div>
                <div style="font-size: 12px; opacity: 0.9;">12.9% surface contact</div>
            </div>
            
            <div style="background: rgba(255,255,255,0.1); padding: 12px; border-radius: 8px;">
                <div style="font-weight: 700; margin-bottom: 5px;">🦶 Ankle Sprains:</div>
                <div style="font-size: 14px;">Landing on opponent's foot</div>
                <div style="font-size: 12px; opacity: 0.9;">Primary contact mechanism</div>
            </div>
        </div>
        
        <div style="margin-top: 15px; font-size: 11px; opacity: 0.8;">
            Source: Stojanovic E, et al. Sports Med. 2025 | IR = Incidence Rate per 100 athlete exposures
        </div>
    </div>
    """, unsafe_allow_html=True)

# ==============================================================================
# USAGE EXAMPLES
# ==============================================================================

"""
# Add to Tab 1 (Today's Readiness):
basketball_injury_research_panel()

# Add to Athlete Profile:
st.markdown("---")
st.markdown("### 🏀 Context-Specific Risk")
injury_mechanism_insight_box(
    athlete_data={'sleep_hours': 6.2, 'soreness': 8, 'acwr': 1.6},
    context="competition"  # or "practice"
)

# Add to sidebar or footer:
quick_reference_card()
"""
