// --------------------------------------------------
// File: ~/RAG_Chatbot/frontend/src/api.js
// Description: FastAPI RAG 서버 API 호출 (최소 사용 버전)
// --------------------------------------------------

// ===== RAG 질의 =====
export async function queryRag(question, sessionId, forcedIntent = null) {
  try {
    const params = new URLSearchParams();

    if (sessionId) {
      params.append("session_id", sessionId);
    }

    if (forcedIntent) {
      params.append("forced_intent", forcedIntent);
    }

    const url =
      params.toString().length > 0
        ? `http://127.0.0.1:8601/rag_query?${params.toString()}`
        : `http://127.0.0.1:8601/rag_query`;

    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });

    return await response.json();
  } catch (err) {
    console.error(err);
    return { error: "API 호출 실패" };
  }
}

// ===== 새 채팅 세션 생성 =====
export async function newChatSession() {
  const response = await fetch("http://127.0.0.1:8601/new_chat_session", {
    method: "POST",
  });
  return response.json();
}

// ===== 메시지 저장 (assistant / user 공통) =====
export async function saveSystemMessage(message, sessionId, role) {
  try {
    const response = await fetch(
      "http://127.0.0.1:8601/save_system_message",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          role: role,
          message: message,
        }),
      }
    );

    return await response.json();
  } catch (err) {
    console.error(err);
    return { error: "API 호출 실패" };
  }
}