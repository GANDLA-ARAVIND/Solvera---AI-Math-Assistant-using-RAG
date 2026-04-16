"""
Feedback Service - Implements the self-learning loop.
Retrieves past corrections and highly-rated answers to ground future responses.
"""

from sqlalchemy import text
from app.database import SessionLocal
from app.models.feedback import Feedback
from app.models.history import SolveHistory


class FeedbackService:
    """Queries past feedback corrections to improve future responses."""

    def get_relevant_corrections(self, query: str, topic: str = None) -> str:
        """
        Look up past corrections from the feedback table for similar topics.
        Returns a formatted string of corrections to include in the LLM prompt.
        """
        db = SessionLocal()
        try:
            # Get corrections (feedback with correction_text) for this topic
            q = (
                db.query(Feedback, SolveHistory)
                .join(SolveHistory, Feedback.history_id == SolveHistory.id)
                .filter(
                    Feedback.feedback_type == "correction",
                    Feedback.correction_text.isnot(None),
                    Feedback.correction_text != "",
                )
            )
            if topic and topic != "general_math":
                q = q.filter(SolveHistory.topic == topic)

            corrections = q.order_by(Feedback.created_at.desc()).limit(5).all()

            if not corrections:
                return ""

            parts = []
            for feedback, history in corrections:
                parts.append(
                    f"- Previous question: \"{history.query_text[:100]}\"\n"
                    f"  Correction: \"{feedback.correction_text[:200]}\""
                )

            return (
                "COMMUNITY CORRECTIONS (from verified feedback):\n"
                + "\n".join(parts)
                + "\nConsider these corrections when formulating your answer."
            )
        except Exception:
            return ""
        finally:
            db.close()

    def get_quality_stats(self, topic: str = None) -> dict:
        """Get feedback quality statistics for a topic."""
        db = SessionLocal()
        try:
            q = (
                db.query(Feedback)
                .join(SolveHistory, Feedback.history_id == SolveHistory.id)
            )
            if topic:
                q = q.filter(SolveHistory.topic == topic)

            feedbacks = q.all()
            if not feedbacks:
                return {"total": 0, "avg_rating": 0, "corrections": 0}

            ratings = [f.rating for f in feedbacks]
            corrections = sum(1 for f in feedbacks if f.correction_text)

            return {
                "total": len(ratings),
                "avg_rating": round(sum(ratings) / len(ratings), 2),
                "corrections": corrections,
            }
        except Exception:
            return {"total": 0, "avg_rating": 0, "corrections": 0}
        finally:
            db.close()


feedback_service = FeedbackService()
