"""
NetSage AI — FastAPI REST API
================================
Exposes the rule checker, case database, dashboard stats, and AI
diagnosis prompt builder as HTTP endpoints.

Usage:
    uvicorn src.api:app --reload --host 0.0.0.0 --port 8000

Endpoints:
    GET   /api/health           Health check
    POST  /api/analyze          Submit a Cisco config for rule checking
    GET   /api/cases            List/filter cases
    GET   /api/cases/{case_id}  Get a single case
    GET   /api/stats            Dashboard statistics
    POST  /api/diagnose         Build diagnosis prompt (or execute via Gemini)

Python 3.10+ | FastAPI + Uvicorn
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ── Local imports ──────────────────────────────
from src.rule_checker import run_all_checks
from src.generate_dashboard import parse_cases, CaseStats

# ── Paths ──────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
CASES_PATH = BASE_DIR / "data" / "cases.csv"
PROMPT_PATH = BASE_DIR / "prompts" / "diagnose_prompt.md"

# ── App ────────────────────────────────────────
app = FastAPI(
    title="NetSage AI API",
    description=(
        "REST API for Cisco network troubleshooting. "
        "Validates configurations, queries a 50-case troubleshooting "
        "dataset, and builds structured AI diagnosis prompts."
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────
# Pydantic Models
# ──────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    """Request body for /api/analyze."""
    config_text: str = Field(
        ...,
        min_length=10,
        description="Full text of a Cisco IOS running-config.",
        json_schema_extra={
            "example": (
                "hostname R1\n!\n"
                "interface GigabitEthernet0/0\n"
                " ip address 192.168.1.1 255.255.255.0\n"
                " no shutdown\n!\nend"
            )
        },
    )


class DiagnosisRequest(BaseModel):
    """Request body for /api/diagnose."""
    symptom: str = Field(
        ...,
        min_length=10,
        description="Description of the observed network problem.",
        json_schema_extra={
            "example": "PC1 cannot reach any host on the 10.0.2.0/24 subnet."
        },
    )
    topology: str = Field(
        default="",
        description="Optional topology note.",
        json_schema_extra={
            "example": "R1 (192.168.1.1/24) — R2 (10.0.2.1/24)"
        },
    )
    show_outputs: str = Field(
        ...,
        min_length=5,
        description="Pasted show-command outputs from the network devices.",
        json_schema_extra={
            "example": (
                ">>> show ip route\n"
                "C 192.168.1.0/24 is directly connected, Gi0/0\n"
            )
        },
    )


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _load_cases() -> list[dict]:
    """Load all cases from the CSV into a list of dicts."""
    if not CASES_PATH.exists():
        return []
    with CASES_PATH.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def _build_prompt(symptom: str, topology: str, show_outputs: str) -> str:
    """Build a diagnosis prompt using the template from diagnose_prompt.md."""
    topo_section = f"\nTOPOLOGY:\n{topology}\n" if topology else ""
    return (
        f"SYMPTOM:\n{symptom}\n"
        f"{topo_section}\n"
        f"SHOW COMMAND OUTPUTS:\n{show_outputs}\n\n"
        f"Diagnose the root cause of this network issue. "
        f"Respond with a single JSON object matching the NetSage AI schema."
    )


def _load_system_prompt() -> str:
    """Load the system prompt from diagnose_prompt.md."""
    if not PROMPT_PATH.exists():
        return ""
    content = PROMPT_PATH.read_text(encoding="utf-8")
    # Extract the system prompt section (between first ```text``` blocks)
    import re
    match = re.search(r"```text\n(.*?)```", content, re.DOTALL)
    return match.group(1).strip() if match else ""


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────

@app.get("/api/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "NetSage AI API",
        "version": "2.0.0",
        "cases_loaded": CASES_PATH.exists(),
    }


@app.post("/api/analyze", tags=["Analysis"])
async def analyze_config(request: AnalyzeRequest):
    """
    Submit a Cisco IOS running-config and receive a deterministic
    rule-checker report with all 15 checks.
    """
    report = run_all_checks(request.config_text, config_file="<api-upload>")
    return report.to_dict()


@app.get("/api/cases", tags=["Cases"])
async def list_cases(
    category: Optional[str] = Query(
        None, description="Filter by category (e.g., VLAN, DHCP, STP)"
    ),
    difficulty: Optional[str] = Query(
        None, description="Filter by difficulty (Easy, Medium, Hard)"
    ),
    osi_layer: Optional[int] = Query(
        None, description="Filter by OSI layer (1-7)", ge=1, le=7
    ),
    concept_tag: Optional[str] = Query(
        None, description="Filter by concept tag (e.g., vlan-configuration)"
    ),
    limit: int = Query(50, description="Max number of results", ge=1, le=100),
    offset: int = Query(0, description="Offset for pagination", ge=0),
):
    """
    List troubleshooting cases with optional filters.
    Returns case metadata without full show-command outputs for brevity.
    """
    cases = _load_cases()

    if category:
        cases = [c for c in cases if c.get("category", "").upper() == category.upper()]
    if difficulty:
        cases = [c for c in cases if c.get("difficulty", "").lower() == difficulty.lower()]
    if osi_layer is not None:
        cases = [c for c in cases if c.get("osi_layer") == str(osi_layer)]
    if concept_tag:
        cases = [c for c in cases if c.get("concept_tag", "").lower() == concept_tag.lower()]

    total = len(cases)
    cases = cases[offset : offset + limit]

    # Return summary fields only (no huge show_commands text)
    results = []
    for c in cases:
        results.append({
            "case_id": c.get("case_id"),
            "category": c.get("category"),
            "symptom": c.get("symptom"),
            "expected_fault": c.get("expected_fault"),
            "osi_layer": int(c["osi_layer"]) if c.get("osi_layer") else None,
            "concept_tag": c.get("concept_tag"),
            "difficulty": c.get("difficulty"),
        })

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "cases": results,
    }


@app.get("/api/cases/{case_id}", tags=["Cases"])
async def get_case(case_id: str):
    """
    Get full details of a single troubleshooting case by ID.
    Includes the complete show-command outputs and topology notes.
    """
    cases = _load_cases()
    case_id_upper = case_id.upper()

    for c in cases:
        if c.get("case_id", "").upper() == case_id_upper:
            return {
                "case_id": c.get("case_id"),
                "category": c.get("category"),
                "symptom": c.get("symptom"),
                "topology_note": c.get("topology_note"),
                "show_commands": c.get("show_commands"),
                "expected_fault": c.get("expected_fault"),
                "osi_layer": int(c["osi_layer"]) if c.get("osi_layer") else None,
                "concept_tag": c.get("concept_tag"),
                "difficulty": c.get("difficulty"),
            }

    raise HTTPException(
        status_code=404,
        detail=f"Case '{case_id}' not found. Use GET /api/cases to list available cases.",
    )


@app.get("/api/stats", tags=["Dashboard"])
async def get_stats():
    """
    Get dashboard statistics: case counts by category, OSI layer,
    difficulty, and list of concept tags.
    """
    if not CASES_PATH.exists():
        raise HTTPException(status_code=500, detail="Cases file not found.")

    stats: CaseStats = parse_cases(CASES_PATH)

    return {
        "total_cases": stats.total_cases,
        "by_category": stats.by_category,
        "by_osi_layer": stats.by_osi_layer,
        "by_difficulty": stats.by_difficulty,
        "concept_tags": stats.concept_tags,
    }


@app.post("/api/diagnose", tags=["Diagnosis"])
async def diagnose_case(
    payload: DiagnosisRequest,
    execute: bool = Query(
        False,
        description=(
            "If false (default), returns only the prepared prompt text. "
            "If true, sends the prompt to Gemini AI and returns the live diagnosis."
        ),
    ),
):
    """
    Build a structured diagnosis prompt from a symptom and show outputs.

    - **execute=false** (default): Returns the prompt text for manual use.
    - **execute=true**: Calls Google Gemini (`gemini-2.5-flash`) and
      returns the AI diagnosis. Requires `GEMINI_API_KEY` env variable.
    """
    user_prompt = _build_prompt(
        payload.symptom, payload.topology, payload.show_outputs
    )
    system_prompt = _load_system_prompt()

    if not execute:
        return {
            "executed": False,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "result": None,
            "model": None,
        }

    # ── Execute via Gemini ────────────────────
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail=(
                "GEMINI_API_KEY environment variable is not set. "
                "Set it to your Google AI API key to enable live diagnosis."
            ),
        )

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail=(
                "google-genai package is not installed. "
                "Run: pip install google-genai"
            ),
        )

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"{system_prompt}\n\n{user_prompt}",
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )
        # Try to parse the response as JSON
        try:
            result = json.loads(response.text)
        except (json.JSONDecodeError, TypeError):
            result = response.text

        return {
            "executed": True,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "result": result,
            "model": "gemini-2.5-flash",
        }
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Gemini API error: {str(e)}",
        )


# ──────────────────────────────────────────────
# Entrypoint
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
