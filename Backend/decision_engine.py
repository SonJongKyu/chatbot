# --------------------------------------------------
# File: ~/RAG_Chatbot/Backend/decision_engine.py
# Description:
# - 질문 → intent 결정
# - rule 기반 + forced_intent 지원
# --------------------------------------------------

from intent_classifier import classify_intent


class DecisionEngine:
    def decide(self, question: str, forced_intent: str = None) -> dict:
        """
        반환 형식:
        {
          "intent": str,
          "confidence": float,
          "reason": str
        }
        """

        # 1️⃣ 강제 intent (버튼/특정 플로우)
        if forced_intent:
            return {
                "intent": forced_intent,
                "confidence": 1.0,
                "reason": "forced_intent"
            }

        # 2️⃣ 규칙 기반 intent 분류
        base = classify_intent(question)

        return {
            "intent": base.get("intent", "AMBIGUOUS"),
            "confidence": float(base.get("confidence", 0.0)),
            "reason": "rule_match"
        }
