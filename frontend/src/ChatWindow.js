// --------------------------------------------------
// File: ~/RAG_Chatbot/frontend/src/ChatWindow.js
// Description: 버튼 기반 시나리오 + 가맹점 조회 (결과 상단 고정)
// --------------------------------------------------

import React, { useState, useRef, useEffect } from "react";
import "./ChatWindow.css";
import {
  queryRag,
  newChatSession,
  saveSystemMessage
} from "./api";

/* ================== 메뉴 정의 ================== */

const MENU_ITEMS = [
  "새 채팅",
  "가맹업무",
  "디지털상품권",
  "지류상품권",
  "부정유통관리",
  "통합관리시스템"
];

const MAIN_BUTTONS = [
  "가맹업무",
  "디지털상품권",
  "지류상품권",
  "부정유통관리",
  "통합관리시스템"
];

const SUB_BUTTONS = {
  "가맹업무": ["신규가맹신청", "가맹기간연장", "한도상향신청"],
  "디지털상품권": ["디지털온누리회원", "디지털상품권결제"],
  "지류상품권": ["상품권발행", "상품권판매", "상품권환전"],
  "부정유통관리": ["부정유통신고", "부정유통조사", "부정유통청문"],
  "통합관리시스템": ["로그인(OTP)", "계정신청", "사용권한"]
};

const MAIN_DISPLAY_MAP = {
  "가맹업무": "가맹업무 관련 안내를 진행하겠습니다.",
  "디지털상품권": "디지털상품권 관련 안내를 진행하겠습니다.",
  "지류상품권": "지류상품권 관련 안내를 진행하겠습니다.",
  "부정유통관리": "부정유통관리 관련 안내를 진행하겠습니다.",
  "통합관리시스템": "통합관리시스템 관련 안내를 진행하겠습니다."
};

const QUESTION_MAP = {
  "신규가맹신청": "신규 가맹 신청 절차를 알려주세요.",
  "가맹기간연장": "가맹 기간 연장 절차를 알려주세요.",
  "한도상향신청": "가맹점 한도 상향 신청 방법을 알려주세요.",
  "디지털온누리회원": "디지털 온누리 회원 가입 방법을 알려주세요.",
  "디지털상품권결제": "디지털 온누리 상품권 결제 방법을 알려주세요.",
  "상품권발행": "지류 상품권 발행 절차를 알려주세요.",
  "상품권판매": "지류 상품권 판매 절차를 알려주세요.",
  "상품권환전": "지류 상품권 환전 절차를 알려주세요.",
  "부정유통신고": "부정 유통 신고 방법을 알려주세요.",
  "부정유통조사": "부정 유통 조사 절차를 알려주세요.",
  "부정유통청문": "부정 유통 청문 절차를 알려주세요.",
  "로그인(OTP)": "통합관리시스템 OTP 로그인 방법을 알려주세요.",
  "계정신청": "통합관리시스템 계정 신청 방법을 알려주세요.",
  "사용권한": "통합관리시스템 사용 권한 설정 방법을 알려주세요."
};

function ChatWindow({ closeChat }) {
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [input, setInput] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);

  const [merchantMode, setMerchantMode] = useState(false);
  const [merchantResult, setMerchantResult] = useState(null);

  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  /* ===== 새 세션 ===== */
  const createNewSession = async () => {
    const res = await newChatSession();
    setSessionId(res.session_id);
    setMessages([]);
    setMerchantMode(false);
    setMerchantResult(null);
    return res.session_id;
  };

  /* ===== 기본 시작 ===== */
  const startMainFlow = async () => {
    const sid = await createNewSession();
    const text = "원하시는 업무를 선택하세요.";
    setMessages([{ sender: "bot", text, buttons: MAIN_BUTTONS }]);
    await saveSystemMessage(text, sid, "assistant");
  };

  /* ===== 가맹점 조회 ===== */
  const startMerchantSearch = async () => {
    const sid = await createNewSession();
    const guide =
      "가맹점 조회를 위해 아래 정보 중 하나 이상을 입력해주세요.\n" +
      "예시)\n- 가맹점명: OO상점\n- 사업자번호: 123-45-67890\n- 가맹주명: 홍길동";
    setMerchantMode(true);
    setMessages([{ sender: "bot", text: guide }]);
    await saveSystemMessage(guide, sid, "assistant");
  };

  /* ===== 메뉴 클릭 ===== */
  const handleMenuClick = async (item) => {
    setMenuOpen(false);

    if (item === "새 채팅") {
      await startMainFlow();
      return;
    }

    const userText = MAIN_DISPLAY_MAP[item];
    if (userText) {
      setMessages(prev => [...prev, { sender: "user", text: userText }]);
      await saveSystemMessage(userText, sessionId, "user");
    }

    const botText = `${item} 항목을 선택하세요.`;
    setMessages(prev => [
      ...prev,
      { sender: "bot", text: botText, buttons: SUB_BUTTONS[item] }
    ]);
    await saveSystemMessage(botText, sessionId, "assistant");
  };

  /* ===== 버튼 클릭 ===== */
  const handleButtonClick = async (btn) => {

    if (SUB_BUTTONS[btn]) {
      const userText = MAIN_DISPLAY_MAP[btn] || btn;

      setMessages(prev => [...prev, { sender: "user", text: userText }]);
      await saveSystemMessage(userText, sessionId, "user");

      const botText = `${btn} 항목을 선택하세요.`;
      setMessages(prev => [
        ...prev,
        { sender: "bot", text: botText, buttons: SUB_BUTTONS[btn] }
      ]);
      await saveSystemMessage(botText, sessionId, "assistant");
      return;
    }

    const question = QUESTION_MAP[btn];
    if (!question) return;

    setMessages(prev => [...prev, { sender: "user", text: question }]);
    await saveSystemMessage(question, sessionId, "user");

    const loadingId = `loading-${Date.now()}`;
    setMessages(prev => [
      ...prev,
      {
        id: loadingId,
        sender: "bot",
        text: "잠시만 기다려주세요. 답변을 생성 중 입니다.",
        className: "loading-spinner" // ⭐ 애니메이션 클래스
      }
    ]);

    const res = await queryRag(question, sessionId);

    setMessages(prev =>
      prev.filter(m => m.id !== loadingId)
          .concat({ sender: "bot", text: res.answer })
    );
    await saveSystemMessage(res.answer, sessionId, "assistant");
  };

  /* ===== 입력 전송 ===== */
  const sendMessage = async () => {
    if (!input.trim()) return;

    const text = input;
    setInput("");

    setMessages(prev => [...prev, { sender: "user", text }]);
    await saveSystemMessage(text, sessionId, "user");

    const loadingId = `loading-${Date.now()}`;
    setMessages(prev => [
      ...prev,
      {
        id: loadingId,
        sender: "bot",
        text: "잠시만 기다려주세요. 답변을 생성 중 입니다.",
        className: "loading-spinner" // ⭐ 애니메이션 클래스
      }
    ]);

    if (merchantMode && !merchantResult) {
      const res = await queryRag(text, sessionId, "MERCHANT_DATA");

      setMessages(prev =>
        prev.filter(m => m.id !== loadingId)
            .concat({ sender: "bot", text: res.answer })
      );
      await saveSystemMessage(res.answer, sessionId, "assistant");

      setMerchantResult(res.answer);
      setMerchantMode(false);
      return;
    }

    const res = await queryRag(text, sessionId);

    setMessages(prev =>
      prev.filter(m => m.id !== loadingId)
          .concat({ sender: "bot", text: res.answer })
    );
    await saveSystemMessage(res.answer, sessionId, "assistant");
  };

  return (
    <div className="chat-window">
      <div className="top-menu">
        <button className="menu-toggle-btn" onClick={() => setMenuOpen(v => !v)}>
          ☰
        </button>

        <button className="merchant-search-btn" onClick={startMerchantSearch}>
          가맹점 조회
        </button>

        {menuOpen && (
          <div className="menu-dropdown">
            {MENU_ITEMS.map((item, i) => (
              <div
                key={i}
                className="menu-item"
                onClick={() => handleMenuClick(item)}
              >
                {item}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="chat-main">
        <div className="chat-header">
          <div className="chat-title">Chatbot</div>
          <button className="close-btn" onClick={closeChat}>✕</button>
        </div>

        {merchantResult && (
          <div className="merchant-info-bar">
            <pre>{merchantResult}</pre>
          </div>
        )}

        <div className="chat-body">
          {messages.map((m, i) => (
            <div
              key={i}
              className={`chat-message ${m.sender} ${m.className || ""}`}
            >
              {m.text}

              {m.buttons && (
                <div className="button-group">
                  {m.buttons.map((b, j) => (
                    <button key={j} onClick={() => handleButtonClick(b)}>
                      {b}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        <div className="chat-input-box">
          <textarea
            value={input}
            placeholder={
              merchantMode
                ? "가맹점 정보를 입력하세요. \nEnter: 전송 / Shift+Enter: 줄바꿈"
                : "질문을 입력하세요. \nEnter: 전송 / Shift+Enter: 줄바꿈"
            }
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && e.shiftKey) return;
              if (e.key === "Enter") {
                e.preventDefault();
                sendMessage();
              }
            }}
          />
          <button onClick={sendMessage}>전송</button>
        </div>
      </div>
    </div>
  );
}

export default ChatWindow;
