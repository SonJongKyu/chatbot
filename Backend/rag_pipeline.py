# --------------------------------------------------
# File: ~/RAG_Chatbot/Backend/rag_pipeline.py
# Description: RAG 전체 파이프라인 오케스트레이터
# --------------------------------------------------

import os
import json

from decision_engine import DecisionEngine
from search_engine import SearchEngine
from formatter import AnswerFormatter


# ==============================
# 세션 저장 경로 설정
# ==============================
BASE_DIR = os.path.join(os.path.expanduser("~"), "RAG_Chatbot")
CHAT_HISTORY_DIR = os.path.join(BASE_DIR, "chat_history_sessions")


# ==============================
# 엔진 인스턴스 (싱글톤)
# ==============================
_decision_engine = DecisionEngine()
_search_engine = SearchEngine()
_formatter = AnswerFormatter()


# ==============================
# 세션에서 active_merchant 로드
# ==============================
def load_active_merchant(session_id: str) -> dict | None:
    if not session_id:
        return None

    path = os.path.join(CHAT_HISTORY_DIR, f"{session_id}.json")
    if not os.path.exists(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            history = json.load(f)
    except Exception:
        return None

    # 최신 가맹점부터 탐색
    for msg in reversed(history):
        merchant = msg.get("active_merchant")
        if isinstance(merchant, dict):
            return merchant

    return None


# ==============================
# 가맹점 컨텍스트 응답
# ==============================
def answer_from_active_merchant(question: str, merchant: dict) -> str | None:
    field_map = {
        "지류": "지류취급여부",
        "전자": "전자취급여부",
        "모바일": "모바일취급여부",
        "한도": "한도금액",
        "사업자": "사업자등록번호"
    }

    for keyword, field in field_map.items():
        if keyword in question and field in merchant:
            name = merchant.get("가맹점명", "해당 가맹점")
            return f"{name}의 {field}는 {merchant[field]}입니다."

    return None


# ==============================
# RAG 파이프라인 단일 진입점
# ==============================
def rag_query(
    question: str,
    session_id: str = None,
    forced_intent: str = None
):
    """
    RAG 파이프라인 단일 진입점

    확장 Flow:
    1. 세션 기반 active_merchant 컨텍스트 질의
    2. Intent 판단 (DecisionEngine)
    3. 문서 검색 (SearchEngine)
    4. Answer 생성 + 포맷 (AnswerFormatter)
    """

    # 🔥 1️⃣ 가맹점 컨텍스트 우선 처리
    active_merchant = load_active_merchant(session_id)
    if active_merchant:
        merchant_answer = answer_from_active_merchant(
            question=question,
            merchant=active_merchant
        )
        if merchant_answer:
            return {
                "type": "MERCHANT_CONTEXT",
                "answer": merchant_answer,
                "confidence": 0.95
            }

    # 🔁 2️⃣ 기존 RAG 흐름
    decision = _decision_engine.decide(
        question=question,
        forced_intent=forced_intent
    )

    candidates = _search_engine.search(
        question=question,
        intent=decision["intent"]
    )

    return _formatter.build_and_format(
        question=question,
        decision=decision,
        candidates=candidates
    )
