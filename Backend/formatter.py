# --------------------------------------------------
# File: ~/RAG_Chatbot/Backend/formatter.py
# Description:
# - Answer 생성
# - LLM 문장 정제 (LAW / ONNURI_KNOWLEDGE만)
# - 출처 문자열 하단 표시 (LAW / ONNURI_KNOWLEDGE만)
# - MERCHANT_DATA는 정형 필드 출력 + 출처/LLM 제외
# --------------------------------------------------

from typing import List, Dict, Any
from langchain_ollama import OllamaLLM


# ===============================
# LLM 공통 규칙
# ===============================
BASE_RULES = """
- 아래 제공된 정보에 없는 내용은 절대 생성하지 마세요.
- 추측, 일반론, 배경 설명은 쓰지 마세요.
- 업무 처리에 바로 쓸 수 있는 답변만 작성하세요.
- 2문장을 넘기지 마세요.
"""

LAW_PROMPT = """
질문:
{question}

법령 근거:
{context}

위 법령을 근거로 질문에 대한 처리 방법만 간결히 작성하세요.
"""

ONNURI_PROMPT = """
질문:
{question}

문서 내용:
{context}

위 내용을 근거로 핵심 안내만 간결히 작성하세요.
"""


class AnswerFormatter:
    def __init__(self):
        self.llm = OllamaLLM(
            model="timHan/llama3korean8B4QKM:latest",
            base_url="http://127.0.0.1:11434",
            max_tokens=200
        )

    # ===============================
    # 메인 진입점
    # ===============================
    def build_and_format(
        self,
        question: str,
        decision: Dict[str, Any],
        candidates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:

        # 1️⃣ 후보 없음
        if not candidates:
            return {
                "type": "NO_MATCH",
                "answer": "관련 정보를 찾을 수 없습니다.",
                "confidence": 0.0
            }

        intent = decision.get("intent", "AMBIGUOUS")
        confidence = float(decision.get("confidence", 0.0))

        # ===============================
        # 2️⃣ MERCHANT_DATA 전용 처리
        # ===============================
        if intent == "MERCHANT_DATA":
            best = candidates[0]
            return {
                "type": "MERCHANT_DATA",
                "answer": self._format_merchant(best),
                "confidence": confidence if confidence > 0 else 0.9
            }

        # ===============================
        # 3️⃣ 기본 Answer 생성
        # ===============================
        best = candidates[0]
        answer_text = self._extract_answer_text(best)

        # ===============================
        # 4️⃣ 출처 문자열 (LAW / ONNURI만)
        # ===============================
        source_text = ""
        if intent in ["LAW", "ONNURI_KNOWLEDGE"]:
            source_text = self._build_source_text(candidates)

        # ===============================
        # 5️⃣ LLM 적용 (LAW / ONNURI만)
        # ===============================
        if intent in ["LAW", "ONNURI_KNOWLEDGE"]:
            answer_text = self._apply_llm(
                question=question,
                intent=intent,
                sources=candidates
            )

        return {
            "type": intent,
            "answer": (answer_text + source_text).strip(),
            "confidence": confidence
        }

    # ===============================
    # MERCHANT_DATA 정형 출력
    # ===============================
    def _format_merchant(self, row: Dict[str, Any]) -> str:
        """
        출력 필드 (존재하는 것만 표시):
        - 가맹점코드
        - 가맹점명
        - 사업자등록번호
        - 지류취급여부
        - 전자취급여부
        - 모바일취급여부
        - 한도금액
        """
        keys = [
            "가맹점코드",
            "가맹점명",
            "사업자등록번호",
            "지류취급여부",
            "전자취급여부",
            "모바일취급여부",
            "한도금액",
        ]

        lines = []
        for k in keys:
            v = row.get(k)
            if v is None or str(v).strip() == "":
                continue
            lines.append(f"{k}: {v}")

        if not lines:
            return "가맹점 정보를 찾았지만 표시할 항목이 없습니다."

        return "\n".join(lines)

    # ===============================
    # 내부 유틸
    # ===============================
    def _extract_answer_text(self, chunk: Dict[str, Any]) -> str:
        if chunk.get("text"):
            return chunk["text"]

        lines = []
        for k, v in chunk.items():
            if k in ["hash", "id", "score", "matched_by"]:
                continue
            if v is None or str(v).strip() == "":
                continue
            lines.append(f"{k}: {v}")

        return "\n".join(lines).strip()

    def _build_source_text(self, candidates: List[Dict[str, Any]]) -> str:
        """
        출력 예:
        [출처] 전통시장법 제26조의6(가맹점 등록의 취소 등)
        [페이지] https://...
        """
        lines = []

        for c in candidates[:2]:
            # 법령
            if c.get("article"):
                law_line = f"[출처] {c.get('file_name')} {c.get('article')}"
                if c.get("title"):
                    law_line += f"({c.get('title')})"
                if c.get("clause") and c.get("clause") != "-":
                    law_line += f" {c.get('clause')}"
                lines.append(law_line)

            # URL
            if c.get("url"):
                lines.append(f"[페이지] {c.get('url')}")

        if not lines:
            return ""

        return "\n\n" + "\n".join(lines)

    def _apply_llm(
        self,
        question: str,
        intent: str,
        sources: List[Dict[str, Any]]
    ) -> str:

        context_parts = []
        for c in sources[:2]:
            parts = []
            for k in ["article", "clause", "title", "text"]:
                if c.get(k):
                    parts.append(str(c.get(k)))
            context_parts.append(" ".join(parts))

        context = "\n".join(context_parts).strip()
        if not context:
            return sources[0].get("text", "")

        if intent == "LAW":
            prompt = BASE_RULES + LAW_PROMPT.format(
                question=question,
                context=context
            )
        else:
            prompt = BASE_RULES + ONNURI_PROMPT.format(
                question=question,
                context=context
            )

        try:
            res = self.llm.generate([prompt])
            text = res.generations[0][0].text.strip()
            return text if text else sources[0].get("text", "")
        except Exception:
            return sources[0].get("text", "")
