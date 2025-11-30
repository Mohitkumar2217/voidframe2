import os
import uvicorn
import traceback
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.vectorstore import FaissVectorStore
from src.dpr_loader import load_dpr_pdf
from src.search import RAGSearch
from src.evaluation import DPRAssistant  # <-- updated assistant
from src.web_search import duckduckgo_search

load_dotenv()

# ---------------------------------------------------
# Initialize FastAPI
# ---------------------------------------------------
app = FastAPI(title="Advanced DPR Intelligence API")

# ---------------------------------------------------
# Ensure required directories exist BEFORE mounting
# ---------------------------------------------------
os.makedirs("uploads", exist_ok=True)
os.makedirs("annotated", exist_ok=True)
os.makedirs("dpr_faiss_store", exist_ok=True)

# ---------------------------------------------------
# Serve static folders
# ---------------------------------------------------
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/annotated", StaticFiles(directory="annotated"), name="annotated")

# ---------------------------------------------------
# CORS
# ---------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ---------------------------------------------------
# FAISS store + RAG engine setup
# ---------------------------------------------------
PERSIST_DIR = "dpr_faiss_store"
store = FaissVectorStore(PERSIST_DIR)
rag = RAGSearch(persist_dir=PERSIST_DIR)

# ---------------------------------------------------
# DPR Assistant (AI Model)
# ---------------------------------------------------
dpr_eval = DPRAssistant()   # uses updated evaluation + annotate_pdf internally


# ----------------------------------------------------------
# 📌 1. Upload DPR → Process → Evaluate → Annotate → Return JSON
# ----------------------------------------------------------
@app.post("/upload_dpr")
async def upload_dpr(file: UploadFile = File(...)):
    try:
        # -----------------------------
        # SAVE THE PDF
        # -----------------------------
        save_path = os.path.join("uploads", file.filename)

        with open(save_path, "wb") as f:
            f.write(await file.read())

        print(f"[INFO] PDF saved at: {save_path}")

        # -----------------------------
        # LOAD PDF INTO TEXT CHUNKS
        # -----------------------------
        docs = load_dpr_pdf(save_path)

        # -----------------------------
        # BUILD FAISS INDEX
        # -----------------------------
        store.build_from_documents(docs)
        store.save()

        # Make RAG use newly built FAISS
        rag.vectorstore = store

        # -----------------------------
        # MERGE ALL TEXT INTO SINGLE DOCUMENT
        # -----------------------------
        dpr_text = "\n\n".join([d.page_content for d in docs])

        # -----------------------------
        # PASS PDF PATH TO AI EVALUATOR
        # -----------------------------
        dpr_eval.input_pdf_path = save_path

        # -----------------------------
        # RUN FULL EVALUATION PIPELINE
        # -----------------------------
        result = dpr_eval.evaluate(dpr_text)

        # result contains:
        # - "report"
        # - "issues"
        # - "highlighted_pdf"

        return {
            "status": "success",
            "evaluation": result["report"],
            "issues": result["issues"],
            "highlighted_pdf": result["highlighted_pdf"]
        }

    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


# ----------------------------------------------------------
# 📌 2. Ask Questions About DPR (RAG)
# ----------------------------------------------------------
class QueryRequest(BaseModel):
    query: str
    top_k: int = 5


@app.post("/ask")
def ask(req: QueryRequest):
    try:
        answer = rag.search_and_summarize(req.query, top_k=req.top_k)
        return {"answer": answer}
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


# ----------------------------------------------------------
# 📌 3. Web Search API
# ----------------------------------------------------------
@app.get("/search_web")
def search_web(q: str):
    try:
        return {"query": q, "results": duckduckgo_search(q)}
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


# ----------------------------------------------------------
# 📌 4. Re-evaluate DPR (without re-uploading)
# ----------------------------------------------------------
@app.post("/evaluate_dpr")
def reevaluate():
    try:
        if not store.safe_load():
            return {"error": "No FAISS index found — upload a DPR first"}

        dpr_text = "\n\n".join([m["text"] for m in store.metadata])

        result = dpr_eval.evaluate(dpr_text)

        return {
            "evaluation": result["report"],
            "issues": result["issues"],
            "highlighted_pdf": result["highlighted_pdf"]
        }

    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


# ----------------------------------------------------------
# 📌 5. Health Check
# ----------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "running"}


# ----------------------------------------------------------
# RUN
# ----------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
