"""
Test Agent
==========

Agent kelima dalam pipeline yang bertugas:
- Membuat test suites (unit, integration, e2e)
- Menggunakan testing framework sesuai tech stack
- Menjamin coverage berdasarkan acceptance criteria

CUSTOMIZATION:
--------------

Untuk menambah dukungan testing framework baru:
1. Tambahkan mapping framework di build_prompt()
2. Tambahkan struktur file test yang sesuai
3. Override process_response() jika perlu parsing khusus

"""

from typing import Dict, Any
from .base import BaseAgent


class TestAgent(BaseAgent):
    """
    Test Agent - membuat test suites berdasarkan spec dan code.

    Agent ini menghasilkan:
    - Unit tests untuk backend
    - Component tests untuk frontend
    - Integration tests untuk API
    - E2E tests jika diperlukan
    """

    # =========================================================================
    # METADATA
    # =========================================================================

    agent_id = "test"
    agent_name = "Testing"
    display_name = "Test Engineer"
    step_order = 5
    description = "Membuat test suites"
    color = "#FFA726"

    # Output: test_plan.md berisi semua test files
    output_fields = [
        ("test_plan", "test_plan.md", "markdown"),
    ]

    # Butuh spec, backend, dan frontend code
    required_fields = ["spec"]

    # =========================================================================
    # PROMPT BUILDING
    # =========================================================================

    def build_prompt(self, state: Dict[str, Any]) -> str:
        """
        Bangun prompt untuk membuat test suites.

        Prompt ini berisi:
        1. Spec dan acceptance criteria
        2. Backend dan frontend code (excerpt)
        3. Mapping testing framework per tech stack
        """
        spec = state.get("spec", "")[:1000]
        acceptance = state.get("acceptance_tests", "")[:1000]
        backend = state.get("backend_code", "")[:1500]
        frontend = state.get("frontend_code", "")[:1500]

        return f"""Kamu adalah Test Engineer Agent.

TUGAS: Buat test suites lengkap sesuai tech stack di spesifikasi.

SPESIFIKASI:
{spec}

ACCEPTANCE CRITERIA:
{acceptance}

BACKEND CODE (excerpt):
{backend}

FRONTEND CODE (excerpt):
{frontend}

LANGKAH PERTAMA - BACA TECH STACK:
Lihat spesifikasi untuk menentukan testing framework yang sesuai:

Backend Testing:
- Node.js/Express -> Jest atau Mocha
- Python/FastAPI/Django -> pytest
- PHP/Laravel -> PHPUnit
- Go/Gin -> Go testing package
- Ruby/Rails -> RSpec
- Java/Spring -> JUnit

Frontend Testing:
- React -> Jest + React Testing Library
- Vue -> Vitest atau Jest + Vue Test Utils
- Angular -> Jasmine + Karma
- Svelte -> Jest + Svelte Testing Library

E2E Testing:
- Playwright, Cypress, atau Selenium

STRUKTUR FILE TEST:
Buat file test sesuai konvensi framework yang digunakan.

{self.get_file_format_instructions()}

Generate setiap file test secara lengkap dan bisa dijalankan."""

    # =========================================================================
    # RESPONSE PROCESSING
    # =========================================================================

    def process_response(self, state: Dict[str, Any], response: Any) -> Dict[str, Any]:
        """
        Proses response dari LLM.

        Simpan hasil ke state["test_plan"].
        """
        state["test_plan"] = response.content
        state["status"] = "tests_created"
        return state


# =============================================================================
# LEGACY FUNCTION (untuk backward compatibility)
# =============================================================================

_agent = TestAgent()


def test_engineer_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy function wrapper untuk backward compatibility."""
    return _agent.execute(state)
