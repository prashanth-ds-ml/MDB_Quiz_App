import streamlit as st

class QuestionDisplay:
    def __init__(self, stats_manager):
        self.stats_manager = stats_manager

    def display_question(self, question_doc, mode="practice"):
        """Display a question with its options"""
        current_domain = self.stats_manager.get_question_domain(question_doc['topic'])

        st.subheader(f"Domain: {current_domain}")
        st.markdown(f"**Topic:** {question_doc['topic']} | **Difficulty:** {question_doc.get('difficulty', 'N/A')}")
        st.markdown(f"**Q: {question_doc['stem']}**")

        # Generate options
        options = [f"{opt['key']}: {opt['text']}" for opt in question_doc["options"]]

        # Different radio button keys for different modes
        radio_key = f"{mode}_answer"
        selected = st.radio("Choose your answer:", options, index=None, key=radio_key)

        return selected, current_domain

    def process_answer(self, selected, question_doc, current_domain, show_explanation=True):
        """Process the submitted answer and update stats"""
        if selected is None:
            st.warning("Please select an answer before submitting.")
            return None

        chosen_key = selected.split(":")[0]
        correct_keys = question_doc["answers"]
        is_correct = chosen_key in correct_keys

        # Update statistics
        self.stats_manager.update_stats(current_domain, is_correct)

        if show_explanation:
            if is_correct:
                st.success("✅ Correct! Great job!")
            else:
                st.error("❌ Incorrect. Don't worry, keep practicing!")

            st.info(f"**Explanation:** {question_doc['explanation']}")

        return is_correct