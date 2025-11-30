import os
import json
import fitz
from dotenv import load_dotenv
from langchain_groq import ChatGroq

from src.web_search import duckduckgo_search
from src.agents import MultiAgentSystem
from src.compliance import ComplianceChecker
from src.benchmarks import CostBenchmarkEngine
from src.boq_parser import extract_boq_sections, parse_boq_from_text, boq_summary
from src.gis_analysis import analyze_site
from src.risk_simulator import run_monte_carlo

# ✅ Correct import name
from src.pdf_annotator import annotate_pdf  

load_dotenv()


class DPRAssistant:

    def __init__(self, model="llama-3.1-8b-instant"):
        self.llm = ChatGroq(
            model=model,
            groq_api_key=os.getenv("GROQ_API_KEY"),
            max_tokens=1800
        )

        self.agents = MultiAgentSystem(strong_mode=True)
        self.compliance_checker = ComplianceChecker()
        self.benchmarks = CostBenchmarkEngine()
        self.input_pdf_path = None  # will be set from FastAPI

    # ----------------------------------------------------------------
    # TEXT CHUNKER
    # ----------------------------------------------------------------
    def _chunk(self, text, size=1500):
        return [text[i:i+size] for i in range(0, len(text), size)]

    # ----------------------------------------------------------------
    # PAGE-LEVEL ISSUE DETECTION
    # ----------------------------------------------------------------
    def detect_page_issues(self, page_text: str, page_num: int):
        prompt = f"""
You are a Government DPR auditor performing page-level analysis.

Return ONLY a JSON list. Each issue must have:
- "snippet": exact text from page (10–40 words, NO paraphrasing)
- "issue": one-line title
- "type": technical | financial | compliance | risk
- "severity": high | medium | low

PAGE NUMBER: {page_num}

PAGE TEXT:
{page_text}

Return JSON ONLY.
"""
        try:
            resp = self.llm.invoke([prompt]).content.strip()
            return json.loads(resp)
        except:
            return []

    # ----------------------------------------------------------------
    # MAIN EVALUATION PIPELINE
    # ----------------------------------------------------------------
    def evaluate(self, dpr_text: str):

        print("[INFO] Running page-by-page issue detection...")

        # --------------------------
        # Detect issues per page
        # --------------------------
        pdf = fitz.open(self.input_pdf_path)
        issues_for_pdf = []

        for p, page in enumerate(pdf):
            page_text = page.get_text()
            page_issues = self.detect_page_issues(page_text, p)

            for issue in page_issues:
                issues_for_pdf.append({
                    "page": p,
                    "snippet": issue.get("snippet", ""),
                    "meta": issue  # contains issue + severity
                })

        pdf.close()

        # --------------------------
        # Chunk for LLM processing
        # --------------------------
        chunks = self._chunk(dpr_text)
        global_context = "\n".join(chunks[:3])

        modules = {
            "Objectives": "Evaluate clarity & justification.",
            "Technical Quality": "Check engineering feasibility.",
            "Financials": "Validate cost vs CPWD/PWD benchmarks.",
            "Timeline": "Check feasibility vs typical Indian norms.",
            "Risks": "Identify major risks & mitigation.",
            "Policy Fit": "Check compliance with Govt schemes.",
            "Sustainability": "Environmental & social assessment."
        }

        module_summaries = []
        print("[INFO] Running structured module evaluation...")

        for title, question in modules.items():

            selected_chunk = global_context
            for ch in chunks:
                if any(w in ch.lower() for w in question.lower().split()):
                    selected_chunk = ch
                    break

            web = duckduckgo_search(
                f"{question} DPR India CPWD MoRTH norms",
                max_results=5
            )
            web_ctx = "\n".join(web)[:1000]

            mod_prompt = f"""
### Module: {title}
### Question: {question}

### DPR Extract:
{selected_chunk[:1400]}

### Web References:
{web_ctx}

Write 200–300 words. End with Score (1–10).
"""

            resp = self.llm.invoke([mod_prompt]).content.strip()
            module_summaries.append(f"## {title}\n{resp}\n")

        # --------------------------
        # Multi-agent system
        # --------------------------
        print("[INFO] Multi-agent review...")
        agent_summary = self.agents.run_full_evaluation(dpr_text)

        # --------------------------
        # BOQ / GIS / RISK
        # --------------------------
        boq_text = extract_boq_sections(dpr_text)
        boq_items = parse_boq_from_text(boq_text)
        boq_stats = boq_summary(boq_items)

        loc_line = next((l for l in dpr_text.splitlines() if "location" in l.lower()), None)
        location = loc_line.split(":", 1)[-1].strip() if loc_line else "India"
        gis_summary = analyze_site(location)

        base_cost = boq_stats.get("total_estimated_cost", 50000000)
        risk_summary = run_monte_carlo(base_cost, base_duration_days=365, n_sims=2000)

        # --------------------------
        # Final LLM synthesis
        # --------------------------
        final_prompt = f"""
Synthesize:
- Module evaluations
- Multi-agent panel
- BOQ analysis
- GIS insights
- Risk simulation

Write a 600-token official DPR evaluation report:
1. Executive Summary
2. Technical Review
3. Financial Review
4. Timeline
5. Risks
6. Policy Compliance
7. Recommendation
"""

        final_report = self.llm.invoke([final_prompt]).content.strip()

        # --------------------------
        # GENERATE HIGHLIGHTED PDF
        # --------------------------
        print("[INFO] Creating highlighted PDF...")

        # ❗ FIX: Correct signature
        highlighted_pdf = annotate_pdf(
            input_path=self.input_pdf_path,   # MATCHES YOUR FUNCTION
            issues=issues_for_pdf
        )

        return {
            "report": final_report,
            "highlighted_pdf": highlighted_pdf,
            "issues": issues_for_pdf
        }
