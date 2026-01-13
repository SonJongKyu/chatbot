# --------------------------------------------------
# File: ~/RAG_Chatbot/Backend/main.py
# Description: FastAPI 기반 RAG 서버 메인 Entry Point
# --------------------------------------------------

from fastapi import FastAPI, UploadFile, File, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import os
import json
from datetime import datetime
import uuid
import threading
import time

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from file_handler import pdf_to_text_with_page, csv_to_text, apply_chunk_strategy
from vector_store import save_faiss, load_faiss_into_memory

# ✅ 앞으로 RAG 진입점은 rag_pipeline로 통일 (rag_service 대체)
from rag_pipeline import rag_query

# ===== 서버 시작 시 FAISS 로드 =====
load_faiss_into_memory()
app = FastAPI()

# ===== CORS 설정 =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== 디렉터리 =====
BASE_DIR = os.path.join(os.path.expanduser("~"), "RAG_Chatbot")
UPLOAD_DIR = os.path.join(BASE_DIR, "input")
CHAT_HISTORY_DIR = os.path.join(BASE_DIR, "chat_history_sessions")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CHAT_HISTORY_DIR, exist_ok=True)

# ===== 세션 저장 파일 경로 =====
def get_session_file(session_id: str):
    return os.path.join(CHAT_HISTORY_DIR, f"{session_id}.json")

# ===== 모델 =====
class Question(BaseModel):
    question: str

class SystemMessage(BaseModel):
    session_id: str
    role: str   # "user" | "bot"
    message: Optional[str] = None

    class Config:
        allow_population_by_field_name = True
        extra = "allow"

@app.get("/")
def read_root():
    return {"status": "ok"}

# ===== 파일 업로드 + 임베딩 =====
@app.post("/upload_file")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as f:
            f.write(await file.read())

        chunks = []
        if file.filename.lower().endswith(".pdf"):
            pages = pdf_to_text_with_page(file_path, file.filename)
            for p in pages:
                for c in apply_chunk_strategy(p["text"], file.filename):
                    chunks.append({"page_no": p["page_no"], "strategy": c.get("strategy"), **c})
        else:
            text = csv_to_text(file_path)
            for c in apply_chunk_strategy(text, file.filename):
                chunks.append({"page_no": "-", "strategy": c.get("strategy"), **c})

        save_faiss(chunks, file_name=file.filename)
        return {"filename": file.filename, "status": "업로드 + 임베딩 완료", "chunks": len(chunks)}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# ===== WATCHER =====
class FileWatcher(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return

        _, ext = os.path.splitext(event.src_path)
        if ext.lower() not in [".pdf", ".csv"]:
            return

        print(f"[WATCHER] 새 파일 감지: {event.src_path}")
        time.sleep(0.5)

        try:
            filename = os.path.basename(event.src_path)
            chunks = []

            if filename.lower().endswith(".pdf"):
                pages = pdf_to_text_with_page(event.src_path, filename)
                for p in pages:
                    for c in apply_chunk_strategy(p["text"], filename):
                        chunks.append({"page_no": p["page_no"], "strategy": c.get("strategy"), **c})
            else:
                text = csv_to_text(event.src_path)
                for c in apply_chunk_strategy(text, filename):
                    chunks.append({"page_no": "-", "strategy": c.get("strategy"), **c})

            save_faiss(chunks, file_name=filename)
            print(f"[WATCHER] {filename} 자동 임베딩 완료 (chunks={len(chunks)})")
        except Exception as e:
            print(f"[WATCHER] 자동 임베딩 오류: {e}")

def start_watcher():
    observer = Observer()
    observer.schedule(FileWatcher(), UPLOAD_DIR, recursive=False)
    observer.start()
    print(f"[WATCHER] input 폴더 감시 시작: {UPLOAD_DIR}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

threading.Thread(target=start_watcher, daemon=True).start()

# ===== 세션 생성 =====
@app.post("/new_chat_session")
def new_chat_session():
    session_id = str(uuid.uuid4())
    with open(get_session_file(session_id), "w", encoding="utf-8") as f:
        json.dump([], f)
    return {"session_id": session_id}

# ===== 메시지 저장 =====
@app.post("/save_system_message")
def save_system_message(data: SystemMessage):
    record = {
        "timestamp": datetime.now().isoformat(),
        "role": data.role,
        "content": data.message
    }

    if data.role == "assistant" and data.message:
        if "가맹점코드:" in data.message:
            record["active_merchant"] = extract_merchant_fields(data.message)

    session_file = get_session_file(data.session_id)
    history = []

    if os.path.exists(session_file):
        try:
            with open(session_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except:
            history = []

    history.append(record)

    with open(session_file, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    return {"status": "ok"}

# ===== RAG QUERY =====
@app.post("/rag_query")
def rag_query_api(
    q: Question,
    session_id: str = Query(None),
    forced_intent: str = Query(None)
):
    return rag_query(
        question=q.question,
        session_id=session_id,
        forced_intent=forced_intent
    )

# ===== 유틸 함수 추가 =====
def extract_merchant_fields(text: str) -> dict:
    """
    '가맹점코드: ...' 형태의 문자열을 dict로 변환
    """
    out = {}
    for line in text.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out
