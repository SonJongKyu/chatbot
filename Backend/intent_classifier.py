# --------------------------------------------------
# File: ~/RAG_Chatbot/Backend/intent_classifier.py
# Description: 경량 규칙 기반 Intent 분류기 (실습용)
# --------------------------------------------------

def classify_intent(question: str) -> dict:
    q = question.strip()

    if not q:
        return {"intent": "AMBIGUOUS", "confidence": 0.0, "scores": {}}

    # ===== MERCHANT_DATA =====
    merchant_keywords = [
        "가맹점", "가맹주", "사업자번호", "가맹점코드"
    ]
    if any(k in q for k in merchant_keywords):
        return {
            "intent": "MERCHANT_DATA",
            "confidence": 0.9,
            "scores": {"MERCHANT_DATA": 0.9}
        }

    # ===== SYSTEM_MENU =====
    menu_keywords = [
        "메뉴", "페이지", "어디서", "경로", "화면", "링크"
    ]
    if any(k in q for k in menu_keywords):
        return {
            "intent": "SYSTEM_MENU",
            "confidence": 0.9,
            "scores": {"SYSTEM_MENU": 0.9}
        }

    # ===== LAW =====
    law_keywords = [
        "법", "법령", "조항", "기준", "시행령", "시행규칙"
    ]
    if any(k in q for k in law_keywords):
        return {
            "intent": "LAW",
            "confidence": 0.9,
            "scores": {"LAW": 0.9}
        }

    # ===== ONNURI_KNOWLEDGE =====
    onnuri_keywords = [
        "온누리", "상품권", "지류", "디지털"
    ]
    if any(k in q for k in onnuri_keywords):
        return {
            "intent": "ONNURI_KNOWLEDGE",
            "confidence": 0.9,
            "scores": {"ONNURI_KNOWLEDGE": 0.9}
        }

    # ===== fallback =====
    return {
        "intent": "AMBIGUOUS",
        "confidence": 0.3,
        "scores": {}
    }
