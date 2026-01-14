"""
QA Agent
========

Agent ketujuh dalam pipeline yang bertugas:
- Code review untuk bug dan tech debt
- Mengidentifikasi issues dengan severity
- Membuat action items untuk perbaikan

CUSTOMIZATION:
--------------

Untuk menambah review criteria:
1. Tambahkan kategori di "Review untuk" section
2. Override build_prompt() untuk instruksi tambahan
3. Ubah output format di process_response() jika perlu

"""

from typing import Dict, Any
from .base import BaseAgent


class QAAgent(BaseAgent):
    """
    QA Agent - melakukan code review dan quality assurance.

    Agent ini menghasilkan:
    - qa_findings.json: Hasil review dengan severity dan recommendations
    """

    # =========================================================================
    # METADATA
    # =========================================================================

    agent_id = "qa"
    agent_name = "QA Review"
    display_name = "QA Critic"
    step_order = 7
    description = "Review kode dan quality assurance"
    color = "#AB47BC"

    # Output: qa_findings.json
    output_fields = [
        ("qa_findings", "qa_findings.json", "json"),
    ]

    # Butuh spec dan code untuk review
    required_fields = ["spec"]

    # =========================================================================
    # PROMPT BUILDING
    # =========================================================================

    def build_prompt(self, state: Dict[str, Any]) -> str:
        """
        Bangun prompt untuk code review.

        Prompt ini berisi:
        1. Spec dan code excerpt
        2. Kriteria review
        3. Format output yang diharapkan
        """
        spec = state.get("spec", "")[:1000]
        backend = state.get("backend_code", "")[:2000]
        frontend = state.get("frontend_code", "")[:2000]

        return f"""Kamu adalah QA Critic Agent.

TUGAS: Review menyeluruh backend dan frontend code.

SPESIFIKASI:
{spec}

BACKEND CODE (excerpt):
{backend}

FRONTEND CODE (excerpt):
{frontend}

FILE YANG HARUS DIBUAT:

1. docs/qa_findings.json - QA review findings dengan format:
   - summary: total issues per severity
   - findings: array dengan id, severity, category, title, description, evidence, recommendation
   - patch_plan: prioritized action items

Review untuk:
- Security vulnerabilities
- Performance issues
- Code duplication / tech debt
- Missing error handling
- UX inconsistencies
- API contract mismatches

{self.get_file_format_instructions()}

Generate file dengan lengkap."""

    # =========================================================================
    # RESPONSE PROCESSING
    # =========================================================================

    def process_response(self, state: Dict[str, Any], response: Any) -> Dict[str, Any]:
        """
        Proses response dari LLM.

        Simpan hasil ke state["qa_findings"].
        """
        state["qa_findings"] = response.content
        state["status"] = "qa_reviewed"
        return state


# =============================================================================
# LEGACY FUNCTION (untuk backward compatibility)
# =============================================================================

_agent = QAAgent()


def qa_critic_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy function wrapper untuk backward compatibility."""
    return _agent.execute(state)
