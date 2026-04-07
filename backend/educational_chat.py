"""SAFE-Triage Educational Module — RAG-grounded explanations with PubMed.

READ-ONLY explanation layer. Never modifies, overrides, or contradicts
the deterministic ESI/NEWS2 engine decisions.

Architecture:
  1. Vertex AI RAG Engine (primary) — retrieves from ESI v5, NEWS2, and
     SAFE-Triage knowledge base documents. Answers grounded ONLY in these.
  2. Context-stuffing fallback — if RAG corpus is not configured, loads
     knowledge base files directly into the Gemini prompt context.
  3. PubMed E-utilities — appends peer-reviewed literature references.
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus
from urllib.request import urlopen, Request

from fastapi import APIRouter
from pydantic import BaseModel

from ai_service import ai_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Educational Chat"])

DISCLAIMER = (
    "\u2695\ufe0f Educational only \u2014 Final triage is determined by the deterministic "
    "ESI/NEWS2 engine and confirmed by the treating clinician. | "
    "\u062a\u0639\u0644\u064a\u0645\u064a \u0641\u0642\u0637 \u2014 "
    "\u0627\u0644\u0641\u0631\u0632 \u0627\u0644\u0646\u0647\u0627\u0626\u064a "
    "\u064a\u062a\u0645 \u0628\u0648\u0627\u0633\u0637\u0629 \u0645\u062d\u0631\u0643 "
    "ESI/NEWS2 \u0627\u0644\u062b\u0627\u0628\u062a \u0648\u064a\u064f\u0624\u0643\u062f "
    "\u0645\u0646 \u0627\u0644\u0637\u0628\u064a\u0628 \u0627\u0644\u0645\u0639\u0627\u0644\u062c."
)

KNOWLEDGE_BASE_DIR = Path(__file__).resolve().parent / "knowledge_base"


# ---------------------------------------------------------------------------
# Vertex AI RAG Engine (primary path)
# ---------------------------------------------------------------------------

_rag_module: Any = None
_rag_model: Any = None  # Dedicated GenerativeModel with RAG tool
_rag_mode: str = "none"  # "rag", "context", or "none"
_context_cache: str = ""  # Loaded knowledge base text for fallback

try:
    from vertexai import rag as _rag_mod_ga
    _rag_module = _rag_mod_ga
except ImportError:
    try:
        from vertexai.preview import rag as _rag_mod_preview
        _rag_module = _rag_mod_preview
    except ImportError:
        _rag_module = None

# Try to import GenerativeModel + Tool for RAG model
try:
    from vertexai.generative_models import GenerativeModel, Tool
except ImportError:
    try:
        from vertexai.preview.generative_models import GenerativeModel, Tool
    except ImportError:
        GenerativeModel = None  # type: ignore[assignment, misc]
        Tool = None  # type: ignore[assignment, misc]


def _init_rag() -> None:
    """Initialize RAG retrieval or fall back to context-stuffing."""
    global _rag_model, _rag_mode, _context_cache

    corpus_name = os.getenv("SAFE_TRIAGE_RAG_CORPUS", "").strip()

    # Path 1: Vertex AI RAG Engine
    if corpus_name and _rag_module and Tool and GenerativeModel:
        try:
            rag_retrieval_tool = Tool.from_retrieval(
                retrieval=_rag_module.Retrieval(
                    source=_rag_module.VertexRagStore(
                        rag_resources=[
                            _rag_module.RagResource(rag_corpus=corpus_name)
                        ],
                        similarity_top_k=5,
                        vector_distance_threshold=0.5,
                    ),
                )
            )
            _rag_model = GenerativeModel(
                "gemini-2.5-flash",
                tools=[rag_retrieval_tool],
            )
            _rag_mode = "rag"
            print(
                f"\u2705 Educational RAG initialized (Vertex AI corpus)",
                flush=True,
            )
            return
        except Exception as e:
            logger.warning("RAG tool init failed, falling back: %s", e)
            print(f"\u26a0\ufe0f RAG init failed: {e} — using context fallback", flush=True)

    # Path 2: Context-stuffing fallback (load KB files into memory)
    if KNOWLEDGE_BASE_DIR.exists():
        parts: List[str] = []
        for txt_file in sorted(KNOWLEDGE_BASE_DIR.glob("*.txt")):
            try:
                content = txt_file.read_text(encoding="utf-8")
                parts.append(content)
            except Exception as e:
                logger.warning("Failed to read %s: %s", txt_file, e)
        if parts:
            _context_cache = "\n\n---\n\n".join(parts)
            _rag_mode = "context"
            print(
                f"\u2705 Educational context loaded ({len(parts)} files, "
                f"{len(_context_cache):,} chars)",
                flush=True,
            )
            return

    _rag_mode = "none"
    print("\u26a0\ufe0f Educational chat: no RAG corpus or knowledge base found", flush=True)


# Initialize on import
_init_rag()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: str
    content: str


class EducationalChatRequest(BaseModel):
    query: str
    esi_level: int
    news2_score: int
    chief_complaint: str
    vitals: Dict[str, Any]
    snomed_code: Optional[str] = None
    snomed_term: Optional[str] = None
    icd10_code: Optional[str] = None
    icd10_description: Optional[str] = None
    language: str = "auto"
    initial_explain: bool = False
    conversation_history: List[ChatMessage] = []


class PubMedReference(BaseModel):
    pmid: str
    title: str
    authors: str
    journal: str
    year: str
    url: str


class EducationalSections(BaseModel):
    protocol_basis: str = ""
    supporting_evidence: str = ""
    clinical_pearls: str = ""
    limitations: str = ""


class EducationalChatResponse(BaseModel):
    answer: str
    sections: Optional[EducationalSections] = None
    pubmed_references: List[PubMedReference]
    language_used: str
    disclaimer: str
    source: str = ""  # "rag", "context", or "general"


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

def _detect_language(text: str) -> str:
    """Return 'ar' if text is primarily Arabic, else 'en'."""
    arabic_count = sum(
        1 for c in text
        if "\u0600" <= c <= "\u06FF" or "\uFE70" <= c <= "\uFEFF"
    )
    total = len(text.replace(" ", ""))
    if total == 0:
        return "en"
    return "ar" if arabic_count / total > 0.3 else "en"


# ---------------------------------------------------------------------------
# PubMed E-utilities integration (free, no API key required)
# ---------------------------------------------------------------------------

def _search_pubmed(
    chief_complaint: str,
    snomed_term: Optional[str] = None,
    icd10_desc: Optional[str] = None,
    max_results: int = 3,
) -> List[PubMedReference]:
    """Search PubMed for relevant triage/emergency medicine articles."""
    search_term = snomed_term or icd10_desc or chief_complaint
    search_term = "".join(
        c for c in search_term
        if not ("\u0600" <= c <= "\u06FF" or "\uFE70" <= c <= "\uFEFF")
    ).strip()
    if not search_term:
        return []

    search_query = f"({search_term}) AND (emergency triage OR ESI OR NEWS2)"

    try:
        search_url = (
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            f"?db=pubmed&retmode=json&retmax={max_results}"
            f"&sort=relevance&term={quote_plus(search_query)}"
        )
        req = Request(search_url, headers={"User-Agent": "SAFE-Triage/2.0"})
        with urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())

        pmids = data.get("esearchresult", {}).get("idlist", [])
        if not pmids:
            return []

        summary_url = (
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
            f"?db=pubmed&retmode=json&id={','.join(pmids)}"
        )
        req = Request(summary_url, headers={"User-Agent": "SAFE-Triage/2.0"})
        with urlopen(req, timeout=5) as resp:
            summary_data = json.loads(resp.read())

        articles: List[PubMedReference] = []
        result_map = summary_data.get("result", {})
        for pmid in pmids:
            article = result_map.get(pmid, {})
            if not isinstance(article, dict) or not article.get("title"):
                continue
            authors_raw = article.get("authors", [])
            author_str = ", ".join(a.get("name", "") for a in authors_raw[:3])
            if len(authors_raw) > 3:
                author_str += " et al."
            pub_date = article.get("pubdate", "")
            articles.append(PubMedReference(
                pmid=pmid,
                title=article.get("title", ""),
                authors=author_str,
                journal=article.get("fulljournalname", article.get("source", "")),
                year=pub_date.split()[0] if pub_date else "",
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            ))
        return articles

    except Exception as e:
        logger.warning("PubMed search failed (non-blocking): %s", e)
        return []


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

_GROUNDING_INSTRUCTION = """CRITICAL: Answer ONLY based on the provided reference documents.
Do NOT use external medical knowledge. If the reference documents do not
contain the answer, say "This is not covered in the protocol documents —
please consult the AHRQ ESI v5 handbook or RCP NEWS2 guidelines directly."
"""

_ROLE_BLOCK = """You are a clinical education assistant integrated into SAFE-Triage,
an emergency department triage system used in Egyptian hospitals.

ROLE: You EXPLAIN triage decisions and teach clinical concepts using ONLY
the ESI v5, NEWS2, and SAFE-Triage protocol documents provided to you.
You NEVER make triage decisions, override them, or suggest changes."""


def _context_block(req: EducationalChatRequest) -> str:
    """Triage context block for the prompt."""
    vitals_str = (
        ", ".join(f"{k}: {v}" for k, v in req.vitals.items())
        if req.vitals else "Not provided"
    )
    snomed_display = req.snomed_code or "Not available"
    if req.snomed_term:
        snomed_display = f"{req.snomed_code} ({req.snomed_term})"
    icd10_display = req.icd10_code or "Not available"
    if req.icd10_description:
        icd10_display = f"{req.icd10_code} ({req.icd10_description})"

    return f"""THE TRIAGE HAS ALREADY BEEN DECIDED:
- ESI Level: {req.esi_level}
- NEWS2 Score: {req.news2_score}
- Chief Complaint: {req.chief_complaint}
- Vital Signs: {vitals_str}
- SNOMED-CT: {snomed_display}
- ICD-10: {icd10_display}"""


def _lang_instruction(language: str) -> str:
    """Language instruction for the prompt."""
    lang_map = {
        "ar": (
            "Respond ENTIRELY in Egyptian Arabic "
            "(\u0639\u0627\u0645\u064a\u0629 \u0645\u0635\u0631\u064a\u0629). "
            "Use Arabic medical terms with English terms in parentheses where helpful."
        ),
        "en": "Respond in clear, professional English.",
        "auto": (
            "Detect the language of the clinician's question. "
            "If Arabic, respond in Egyptian Arabic. "
            "If English, respond in English. If mixed, match the dominant language."
        ),
    }
    return lang_map.get(language, lang_map["auto"])


def _build_initial_prompt(
    req: EducationalChatRequest,
    language: str,
    knowledge_context: str,
) -> str:
    """Prompt for structured initial explanation (returns JSON)."""
    kb_block = ""
    if knowledge_context:
        kb_block = (
            "\n\n=== REFERENCE DOCUMENTS (answer ONLY from these) ===\n"
            + knowledge_context
            + "\n=== END REFERENCE DOCUMENTS ===\n"
        )

    return f"""{_ROLE_BLOCK}

{_GROUNDING_INSTRUCTION if knowledge_context else ""}
{_context_block(req)}
{kb_block}
{_lang_instruction(language)}

Provide a structured educational explanation of this triage decision.
Return ONLY valid JSON (no markdown fences, no extra text) with these exact keys:

{{
  "protocol_basis": "2-3 sentences explaining WHY this ESI level was assigned. Reference the specific ESI v5 Decision Point (A: immediate life-saving, B: high-risk/shouldn't wait, C: resource count, D: danger zone vitals) that determined this level. Cite the exact thresholds from the protocol.",
  "supporting_evidence": "2-3 sentences about the clinical evidence — which vital signs are abnormal, their individual NEWS2 scores, what red flags are present, and what the NEWS2 total means per the scoring guide.",
  "clinical_pearls": "2-3 sentences teaching the clinician something useful from the protocols — safety floor rules that applied, context rules (silent MI, atypical ACS, sepsis screening) if relevant, or common pitfalls.",
  "limitations": "1 sentence about what the protocol documents cannot address — e.g., patient-specific comorbidities, clinical gestalt, or factors requiring bedside assessment."
}}

Keep each section concise. This is a busy ED."""


def _build_followup_prompt(
    req: EducationalChatRequest,
    language: str,
    knowledge_context: str,
) -> str:
    """Prompt for follow-up Q&A (returns plain text)."""
    history_block = ""
    if req.conversation_history:
        turns = []
        for msg in req.conversation_history[-6:]:
            role_label = "Clinician" if msg.role == "user" else "Assistant"
            turns.append(f"{role_label}: {msg.content}")
        history_block = "\n\nPREVIOUS CONVERSATION:\n" + "\n".join(turns) + "\n"

    kb_block = ""
    if knowledge_context:
        kb_block = (
            "\n\n=== REFERENCE DOCUMENTS (answer ONLY from these) ===\n"
            + knowledge_context
            + "\n=== END REFERENCE DOCUMENTS ===\n"
        )

    return f"""{_ROLE_BLOCK}

{_GROUNDING_INSTRUCTION if knowledge_context else ""}
{_context_block(req)}
{kb_block}{history_block}
CLINICIAN'S QUESTION: {req.query}

INSTRUCTIONS:
1. Answer ONLY using information from the reference documents provided above.
2. Reference specific ESI Decision Points (A/B/C/D), NEWS2 thresholds, and safety floor rules by their exact values.
3. If the question is about something not in the documents, say so clearly.
4. Keep it concise — 2-4 paragraphs max. This is a busy ED.
5. NEVER suggest changing the ESI level — the decision is final.

{_lang_instruction(language)}

Respond in plain text with paragraph breaks. No markdown."""


def _parse_sections(text: str) -> Optional[EducationalSections]:
    """Parse structured JSON sections from Gemini response."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict) and "protocol_basis" in data:
            return EducationalSections(
                protocol_basis=data.get("protocol_basis", ""),
                supporting_evidence=data.get("supporting_evidence", ""),
                clinical_pearls=data.get("clinical_pearls", ""),
                limitations=data.get("limitations", ""),
            )
    except (json.JSONDecodeError, TypeError):
        pass
    return None


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/educational-chat", response_model=EducationalChatResponse)
async def educational_chat(req: EducationalChatRequest):
    """Educational module — RAG-grounded explanations + follow-up Q&A.

    Retrieval priority:
      1. Vertex AI RAG Engine (if SAFE_TRIAGE_RAG_CORPUS is set)
      2. Context-stuffing from knowledge_base/ files
      3. General Gemini knowledge (last resort)

    Always includes PubMed references and bilingual disclaimer.
    """
    language = req.language if req.language != "auto" else _detect_language(req.query)

    # --- Determine knowledge context based on RAG mode ---
    knowledge_context = ""
    source = _rag_mode

    if _rag_mode == "context":
        knowledge_context = _context_cache
    # For "rag" mode, the RAG tool handles retrieval automatically

    # --- Build prompt ---
    if req.initial_explain:
        prompt = _build_initial_prompt(req, language, knowledge_context)
    else:
        prompt = _build_followup_prompt(req, language, knowledge_context)

    # --- Gemini call (with RAG tool or context-stuffed) ---
    answer = ""
    sections: Optional[EducationalSections] = None
    try:
        timeout = float(os.getenv("EDUCATIONAL_CHAT_TIMEOUT", "30.0"))

        if _rag_mode == "rag" and _rag_model:
            # Path 1: Vertex AI RAG — model has retrieval tool attached.
            # Gemini auto-retrieves from corpus before generating.
            started = __import__("time").perf_counter()
            future = ai_service._executor.submit(
                _rag_model.generate_content, prompt
            )
            response = future.result(timeout=timeout)
            elapsed = __import__("time").perf_counter() - started
            print(
                f"[Timing] educational chat (RAG): {elapsed:.3f}s",
                flush=True,
            )
        else:
            # Path 2/3: Context-stuffed or general knowledge
            if not ai_service.client:
                raise RuntimeError("AI service unavailable")
            response = ai_service._generate_content_with_timeout(
                prompt,
                timeout_seconds=timeout,
                label="educational chat",
            )

        raw_text = response.text.strip()

        if req.initial_explain:
            sections = _parse_sections(raw_text)
            if sections:
                answer = sections.protocol_basis
            else:
                answer = raw_text
                sections = EducationalSections(protocol_basis=raw_text)
        else:
            answer = raw_text

    except Exception as e:
        logger.error("Educational chat Gemini error: %s", e)
        answer = (
            "\u0639\u0630\u0631\u0627\u064b\u060c \u062d\u062f\u062b \u062e\u0637\u0623 "
            "\u0641\u064a \u062a\u0648\u0644\u064a\u062f \u0627\u0644\u0634\u0631\u062d. "
            "\u064a\u0631\u062c\u0649 \u0627\u0644\u0645\u062d\u0627\u0648\u0644\u0629 "
            "\u0645\u0631\u0629 \u0623\u062e\u0631\u0649. | "
            "Sorry, an error occurred generating the explanation. Please try again."
        )
        source = "error"

    # --- PubMed references (non-blocking) ---
    pubmed_refs = _search_pubmed(
        chief_complaint=req.chief_complaint,
        snomed_term=req.snomed_term,
        icd10_desc=req.icd10_description,
    )

    print(
        f"[Educational Chat] source={source}, "
        f"mode={'initial' if req.initial_explain else 'followup'}, "
        f"lang={language}, pubmed_hits={len(pubmed_refs)}",
        flush=True,
    )

    return EducationalChatResponse(
        answer=answer,
        sections=sections,
        pubmed_references=pubmed_refs,
        language_used=language,
        disclaimer=DISCLAIMER,
        source=source,
    )
