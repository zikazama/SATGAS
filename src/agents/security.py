"""
Security Agent
==============

Agent keenam dalam pipeline yang bertugas:
- Threat modeling (STRIDE analysis)
- Security requirements checklist
- Security findings dari code review

CUSTOMIZATION:
--------------

Untuk menambah security check:
1. Tambahkan kategori baru di FILE YANG HARUS DIBUAT
2. Override build_prompt() untuk menambah instruksi
3. Tambah output_fields jika membuat file baru

"""

from typing import Dict, Any
from .base import BaseAgent


class SecurityAgent(BaseAgent):
    """
    Security Agent - melakukan security analysis dan threat modeling.

    Agent ini menghasilkan:
    - threat_model.md: STRIDE analysis dan risk matrix
    - security_requirements.md: Security checklist
    - security_findings.json: Hasil code review untuk security issues
    """

    # =========================================================================
    # METADATA
    # =========================================================================

    agent_id = "security"
    agent_name = "Security"
    display_name = "Security"
    step_order = 6
    description = "Threat modeling dan security checks"
    color = "#EF5350"

    # Output: 3 security documents
    output_fields = [
        ("threat_model", "threat_model.md", "markdown"),
        ("security_requirements", "security_requirements.md", "markdown"),
        ("security_findings", "security_findings.json", "json"),
    ]

    # Butuh spec dan code untuk review
    required_fields = ["spec"]

    # =========================================================================
    # PROMPT BUILDING
    # =========================================================================

    def build_prompt(self, state: Dict[str, Any]) -> str:
        """
        Bangun prompt untuk security analysis.

        Prompt ini berisi:
        1. Spec dan code excerpt untuk review
        2. Template untuk threat model
        3. Security checklist items
        """
        spec = state.get("spec", "")[:1500]
        backend = state.get("backend_code", "")[:1500]
        frontend = state.get("frontend_code", "")[:1000]

        return f"""Kamu adalah Security/AppSec Agent.

TUGAS: Buat threat model, security requirements, dan security findings.

SPESIFIKASI:
{spec}

BACKEND CODE (excerpt):
{backend}

FRONTEND CODE (excerpt):
{frontend}

FILE YANG HARUS DIBUAT:

1. docs/threat_model.md - Threat modeling dengan:
   - Assets yang dilindungi
   - Threat actors
   - Attack vectors & mitigations (tabel)
   - STRIDE analysis
   - Risk matrix

2. docs/security_requirements.md - Security checklist untuk:
   - Authentication (password, JWT, lockout)
   - Authorization (RBAC)
   - Input validation
   - Session management
   - API security
   - Security headers
   - Secrets management

3. docs/security_findings.json - Review kode untuk security issues:
   - Severity (critical/high/medium/low)
   - Category (auth/injection/xss/config)
   - Location dan recommendation

{self.get_file_format_instructions()}

Generate setiap file secara lengkap."""

    # =========================================================================
    # RESPONSE PROCESSING
    # =========================================================================

    def process_response(self, state: Dict[str, Any], response: Any) -> Dict[str, Any]:
        """
        Proses response dari LLM.

        Simpan ke 3 state fields karena LLM menggenerate semua
        dokumen dalam satu output.
        """
        state["threat_model"] = response.content
        state["security_requirements"] = response.content
        state["security_findings"] = response.content
        state["status"] = "security_checked"
        return state


# =============================================================================
# LEGACY FUNCTION (untuk backward compatibility)
# =============================================================================

_agent = SecurityAgent()


def security_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy function wrapper untuk backward compatibility."""
    return _agent.execute(state)
