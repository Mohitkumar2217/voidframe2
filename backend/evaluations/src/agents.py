# src/agents.py
import os
from typing import Dict, Any
from dotenv import load_dotenv
from langchain_groq import ChatGroq

from src.web_search import duckduckgo_search

load_dotenv()

# Recommended agent model (fast + supported in your account)
DEFAULT_AGENT_MODEL = os.getenv("AGENT_MODEL", "llama-3.1-8b-instant")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


def _trim(text: str, chars: int = 1400) -> str:
    """Trim text safely for token limits (preserve start & end if large)."""
    if not text:
        return ""
    if len(text) <= chars:
        return text
    # keep first 1000 and last 400 chars for context continuity
    return text[:1000] + "\n\n...[TRIMMED]...\n\n" + text[-400:]


class MultiAgentSystem:
    """
    Multi-agent DPR evaluation system with optional strong_mode.

    - strong_mode=True -> each agent performs web-validated reasoning,
      deeper prompts, and returns more structured output.
    - strong_mode=False -> lighter, faster outputs (still LLM-based).
    """

    def __init__(self, strong_mode: bool = False, model: str = DEFAULT_AGENT_MODEL, max_tokens: int = 900):
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not found in environment.")
        self.strong_mode = strong_mode
        self.model = model
        self.llm = ChatGroq(
            model=self.model,
            groq_api_key=GROQ_API_KEY,
            max_tokens=max_tokens
        )

    # -------------------------
    # Engineer Agent
    # -------------------------
    def engineer_agent(self, dpr_context: str) -> str:
        ctx = _trim(dpr_context)
        if self.strong_mode:
            # fetch web evidence for engineering standards
            web = duckduckgo_search("MoRTH standards engineering typical DPR design guidelines CPWD", max_results=4)
            web_ctx = "\n".join(web)[:900]
            prompt = f"""
You are a Senior Civil/Structural Engineer evaluating a DPR.

DPR excerpt (trimmed):
{ctx}

Web evidence (authoritative sources, trimmed):
{web_ctx}

Tasks (strong mode):
- Quickly identify major engineering flaws, missing design elements, or compliance gaps.
- Check if materials/sections/specs match MoRTH/CPWD/standard practice; mention mismatches.
- Provide top 5 technical concerns (short bullets).
- Provide 3 practical mitigation suggestions.
- Give a Technical Score (1-10) and a confidence level (low/medium/high).

Output format:
- Bullet list of concerns
- Bullet list of mitigations
- Technical Score: X/10
- Confidence: <low|medium|high>
"""
        else:
            prompt = f"""
You are a Civil/Structural Engineer.

DPR excerpt:
{ctx}

Tasks:
- List up to 5 technical concerns (bullets).
- Give 1-2 mitigations.
- Technical Score (1-10).

Output as bullets and one score line.
"""
        resp = self.llm.invoke([prompt]).content.strip()
        return f"Engineer Agent Output:\n{resp}"

    # -------------------------
    # Finance Agent
    # -------------------------
    def finance_agent(self, dpr_context: str) -> str:
        ctx = _trim(dpr_context)
        if self.strong_mode:
            # get CPWD/PWD/market rate snippets
            web = duckduckgo_search("CPWD schedule of rates 2024 typical unit rates road construction India", max_results=4)
            web_ctx = "\n".join(web)[:900]
            prompt = f"""
You are a Senior Cost/Finance Analyst for government DPRs.

DPR excerpt:
{ctx}

Web benchmarks:
{web_ctx}

Tasks:
- Identify suspicious/inflated unit rates and missing cost heads.
- Estimate whether total cost is reasonable vs web benchmarks; state percentage over/under if detectable.
- Provide 3 recommendations to reduce cost or clarify BOQ.
- Return Finance Score (1-10) and confidence.

Output:
- Bulleted findings
- Cost delta estimate if possible (e.g., DPR cost is ~20% higher than benchmark)
- Finance Score: X/10
- Confidence: <low|medium|high>
"""
        else:
            prompt = f"""
You are a Finance Analyst.

DPR excerpt:
{ctx}

Tasks:
- List cost concerns (bullets).
- Give 1-2 recommendations.
- Finance Score (1-10).

Output concise.
"""
        resp = self.llm.invoke([prompt]).content.strip()
        return f"Finance Agent Output:\n{resp}"

    # -------------------------
    # Risk Agent
    # -------------------------
    def risk_agent(self, dpr_context: str, monte_carlo_summary: Dict[str, Any] | None = None) -> str:
        ctx = _trim(dpr_context)
        mc_snip = ""
        if monte_carlo_summary:
            # present a short human-readable summary of risk sim
            mc_snip = f"Monte Carlo summary (median cost {monte_carlo_summary.get('cost', {}).get('p50', 'N/A')}, p90 overrun pct {monte_carlo_summary.get('cost_overrun_distribution_pct', {}).get('p90', 'N/A')}%)"
        if self.strong_mode:
            web = duckduckgo_search("project risk common failure modes construction project India delays cost overrun", max_results=3)
            web_ctx = "\n".join(web)[:700]
            prompt = f"""
You are a Risk Analyst specialized in infrastructure DPRs.

DPR excerpt:
{ctx}

Monte Carlo summary:
{mc_snip}

Relevant web insights:
{web_ctx}

Tasks:
- Identify top 6 risks (technical, financial, environmental, institutional).
- For each risk, give likelihood (low/medium/high) and impact (low/medium/high).
- Provide prioritized mitigation measures.
- Provide an overall Risk Level (Low/Medium/High) and Risk Score (1-10).

Output as a short risk table, then score & level.
"""
        else:
            prompt = f"""
You are a Risk Analyst.

DPR excerpt:
{ctx}

Tasks:
- List top 4 risks with likelihood & impact (brief).
- Risk Score (1-10).

Output concise.
"""
        resp = self.llm.invoke([prompt]).content.strip()
        return f"Risk Agent Output:\n{resp}"

    # -------------------------
    # Policy Agent
    # -------------------------
    def policy_agent(self, dpr_context: str) -> str:
        ctx = _trim(dpr_context)
        if self.strong_mode:
            # probe scheme-specific checks
            web = duckduckgo_search("PMGSY DPR guidelines format MoRTH DPR checklist", max_results=5)
            web_ctx = "\n".join(web)[:900]
            prompt = f"""
You are a Government Policy & Compliance Specialist.

DPR excerpt:
{ctx}

Scheme references:
{web_ctx}

Tasks:
- Check DPR alignment with PMGSY/AMRUT/JJM/Smart Cities/MoRTH where applicable.
- Flag missing statutory approvals or statutory documents.
- Provide compliance score per scheme (0-10).
- Recommend exact documents or clauses needed to fix compliance.

Output structured: Scheme -> [Compliant/Partial/Not Compliant], Score, Fixes.
"""
        else:
            prompt = f"""
You are a Policy Analyst.

DPR excerpt:
{ctx}

Tasks:
- Identify any obvious policy or compliance gaps.
- Provide a short compliance score (1-10).
"""
        resp = self.llm.invoke([prompt]).content.strip()
        return f"Policy Agent Output:\n{resp}"

    # -------------------------
    # Reviewer / Aggregator Agent
    # -------------------------
    def reviewer_agent(self, engineer_out: str, finance_out: str, risk_out: str, policy_out: str) -> str:
        """
        Combine agent outputs into a short consolidated evaluation.
        """
        # Trim inputs to stay token-safe
        e = _trim(engineer_out, chars=1200)
        f = _trim(finance_out, chars=1200)
        r = _trim(risk_out, chars=1200)
        p = _trim(policy_out, chars=1200)

        prompt = f"""
You are the Final Reviewer that must combine outputs from specialist agents.

Engineer:
{e}

Finance:
{f}

Risk:
{r}

Policy:
{p}

Tasks:
- Provide a 6-8 line executive summary synthesizing the 4 agents.
- Provide consolidated Strengths (3 bullets) and Weaknesses (3 bullets).
- Produce a combined Scorecard: Technical / Finance / Risk / Compliance (each 0-10).
- Give a single Recommendation: Go / Revise / No-Go with 3 reasons.

Keep output concise and actionable.
"""
        resp = self.llm.invoke([prompt]).content.strip()
        return f"Reviewer Agent Output:\n{resp}"

    # -------------------------
    # High-level helper: run all agents and return consolidated result
    # -------------------------
    def run_full_evaluation(self, dpr_text: str, monte_carlo_summary: Dict[str, Any] | None = None) -> str:
        """
        Runs all agents sequentially (engineer, finance, risk, policy) and then the reviewer.
        Returns a combined textual summary.
        """
        # Use trimmed full context for speed
        context = _trim(dpr_text, chars=3000)

        # Run agents
        eng = self.engineer_agent(context)
        fin = self.finance_agent(context)
        risk = self.risk_agent(context, monte_carlo_summary=monte_carlo_summary)
        pol = self.policy_agent(context)

        # Final aggregate
        review = self.reviewer_agent(eng, fin, risk, pol)

        # Return a composite structure
        out = {
            "engineer": eng,
            "finance": fin,
            "risk": risk,
            "policy": pol,
            "reviewer": review
        }

        # Format compactly for insertion into final prompt
        formatted = "\n\n--- AGENT PANEL ---\n"
        formatted += f"Engineer:\n{eng}\n\n"
        formatted += f"Finance:\n{fin}\n\n"
        formatted += f"Risk:\n{risk}\n\n"
        formatted += f"Policy:\n{pol}\n\n"
        formatted += f"Reviewer:\n{review}\n"
        return formatted
