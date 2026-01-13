# --------------------------------------------------
# File: ~/RAG_Chatbot/Backend/search_engine.py
# Description:
# - doc_profiles.json 기반 검색 엔진
# - FAISS / CSV 검색 수행
# - Formatter 친화적 dict 결과 반환
# --------------------------------------------------

from typing import List, Dict, Any
import os
import json

import vector_store
from vector_store import search_faiss
from ranking import hybrid_rank


# ✅ 가맹점 조회에 사용할 필드만
CSV_FIELDS = ["가맹점코드", "가맹점명", "사업자등록번호"]


# doc_profiles.json 경로
BASE_DIR = os.path.join(os.path.expanduser("~"), "RAG_Chatbot")
DOC_PROFILES_PATH = os.path.join(BASE_DIR, "doc_profiles.json")


class SearchEngine:
    def __init__(self):
        self.profiles = self._load_profiles()

    # ===============================
    # public
    # ===============================
    def search(self, question: str, intent: str) -> List[Dict[str, Any]]:
        """
        intent에 해당하는 문서 프로필 기준으로 검색 수행
        반환값: Formatter가 바로 쓰는 dict 리스트
        """
        intent_cfg = self.profiles.get("intents", {}).get(intent)
        if not intent_cfg:
            return []

        # ✅ 가맹점 조회는 CSV 전용 로직
        if intent == "MERCHANT_DATA":
            return self._search_csv(question, intent_cfg)

        return self._search_faiss(question, intent_cfg)

    def reload_profiles(self):
        """doc_profiles.json 수정 후 핫 리로드용"""
        self.profiles = self._load_profiles()

    # ===============================
    # internal
    # ===============================
    def _load_profiles(self) -> Dict[str, Any]:
        if not os.path.exists(DOC_PROFILES_PATH):
            return {"intents": {}}
        try:
            with open(DOC_PROFILES_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"intents": {}}

    def _search_faiss(self, question: str, cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
        top_k = int(cfg.get("top_k", 3))
        files = cfg.get("files")
        strategies = cfg.get("strategies")
        use_hybrid = bool(cfg.get("use_hybrid_rank", False))

        candidates: List[Dict[str, Any]] = []

        # 전략 1개
        if strategies and len(strategies) == 1:
            candidates = search_faiss(
                question,
                top_k=top_k,
                strategy_filter=strategies[0],
                file_name_filter=files
            )

        # 전략 여러 개
        else:
            if not strategies:
                strategies = [None]

            for st in strategies:
                results = search_faiss(
                    question,
                    top_k=top_k,
                    strategy_filter=st,
                    file_name_filter=files
                )
                candidates.extend(results)

            # 중복 제거 (hash 또는 id 기준)
            seen = set()
            uniq = []
            for r in candidates:
                key = r.get("hash") or r.get("id")
                if key in seen:
                    continue
                seen.add(key)
                uniq.append(r)
            candidates = uniq

        if not candidates:
            return []

        # 하이브리드 랭킹
        if use_hybrid:
            candidates = hybrid_rank(question, candidates)

        # score / matched_by 보강
        reason = self._build_reason(cfg)
        out = []
        for r in candidates[:top_k]:
            out.append({
                **r,
                "matched_by": [reason]
            })

        return out

    def _search_csv(self, query: str, cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        ✅ 가맹점 조회 전용 CSV 검색
        - 파일 필터 필수
        - strategy == csv 만 허용
        - 토큰 기반 exact → partial
        - 결과는 1건만 반환 (UX 고정)
        """
        if not query:
            return []

        allowed_files = cfg.get("files") or []
        if not allowed_files:
            return []

        # ---------------------------
        # 0) 토큰 분해 (문장형 입력 대응)
        # ---------------------------
        tokens = (
            query.replace(",", " ")
                .replace(":", " ")
                .strip()
                .split()
        )

        if not tokens:
            return []

        # ---------------------------
        # 1) exact match (토큰 단위)
        # ---------------------------
        for m in vector_store.metadata:
            if m.get("file_name") not in allowed_files:
                continue
            if m.get("strategy") != "csv":
                continue

            for t in tokens:
                if any((m.get(k) or "") == t for k in CSV_FIELDS):
                    return [{
                        **m,
                        "score": 1.0,
                        "matched_by": ["csv.exact"]
                    }]

        # ---------------------------
        # 2) partial match (토큰 단위)
        # ---------------------------
        for m in vector_store.metadata:
            if m.get("file_name") not in allowed_files:
                continue
            if m.get("strategy") != "csv":
                continue

            for t in tokens:
                if any(t in (m.get(k, "") or "") for k in CSV_FIELDS):
                    return [{
                        **m,
                        "score": 0.8,
                        "matched_by": ["csv.partial"]
                    }]

        return []


    def _build_reason(self, cfg: Dict[str, Any]) -> str:
        st = cfg.get("strategies")
        if st:
            return f"semantic:{','.join(st)}"
        return "semantic"
