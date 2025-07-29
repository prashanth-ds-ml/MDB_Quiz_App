
import streamlit as st
import plotly.express as px
import pandas as pd

class Dashboard:
    def __init__(self, stats_manager):
        self.stats_manager = stats_manager
    
    def display_overview_metrics(self):
        """Display overall performance metrics"""
        total_questions, total_correct, overall_accuracy = self.stats_manager.get_overall_stats()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📝 Total Questions", total_questions)
        with col2:
            st.metric("✅ Correct Answers", total_correct)
        with col3:
            st.metric("🎯 Overall Accuracy", f"{overall_accuracy}%")
    
    def display_domain_performance(self):
        """Display domain-wise performance charts and tables"""
        st.subheader("📈 Performance by Exam Domain")
        
        domain_data = self.stats_manager.get_domain_data()
        
        if domain_data and any(d["Questions Attempted"] > 0 for d in domain_data):
            df = pd.DataFrame(domain_data)
            df_filtered = df[df["Questions Attempted"] > 0]
            
            # Accuracy chart
            fig = px.bar(df_filtered, x="Domain", y="Accuracy (%)", 
                         title="Accuracy by Exam Domain",
                         color="Accuracy (%)",
                         color_continuous_scale="RdYlGn")
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
            
            # Detailed stats table
            st.subheader("📋 Detailed Statistics")
            st.dataframe(df_filtered, use_container_width=True)
            
            return df_filtered
        else:
            st.info("Start practicing to see your progress!")
            return None
    
    def display_recommendations(self, domain_data):
        """Display study recommendations"""
        if domain_data is not None:
            st.subheader("💡 Study Recommendations")
            weak_areas, strong_areas, untested_areas = self.stats_manager.get_recommendations(
                domain_data.to_dict('records')
            )
            
            if weak_areas:
                st.warning(f"**Focus on these areas:** {', '.join(weak_areas)}")
            if strong_areas:
                st.success(f"**Great job on:** {', '.join(strong_areas)}")
            if untested_areas:
                st.info(f"**Haven't practiced yet:** {', '.join(untested_areas)}")
