"""
Frontend Agent
==============

Agent keempat dalam pipeline yang bertugas:
- Implementasi frontend sesuai tech stack di spec
- Membuat komponen UI, routing, dan state management
- Integrasi dengan backend API

CUSTOMIZATION:
--------------

Untuk menambah dukungan framework baru:
1. Tambahkan entry di FRONTEND_STACKS di config/settings.py
2. Agent akan otomatis menggunakan struktur yang didefinisikan

"""

from typing import Dict, Any
from .base import BaseAgent
from config.settings import FRONTEND_STACKS


def _format_frontend_structures() -> str:
    """Format struktur file dari FRONTEND_STACKS untuk prompt."""
    lines = []
    for key, stack in FRONTEND_STACKS.items():
        name = stack["name"]
        structure = ", ".join(stack["structure"])
        lines.append(f"{name}:\n- {structure}")
    return "\n\n".join(lines)


class FrontendAgent(BaseAgent):
    """
    Frontend Agent - implementasi frontend berdasarkan spesifikasi.

    Agent ini menghasilkan file frontend sesuai tech stack:
    - React: package.json, src/App.jsx, components, pages, hooks
    - Vue: package.json, src/App.vue, components, views, composables
    - Angular: package.json, app.component.ts, components, services
    - Dan framework lainnya
    """

    # =========================================================================
    # METADATA
    # =========================================================================

    agent_id = "frontend"
    agent_name = "Frontend"
    display_name = "Frontend Engineer"
    step_order = 4
    description = "Implementasi UI dan UX"
    color = "#66BB6A"

    # Output: frontend code (semua file frontend dalam satu output)
    output_fields = [
        ("frontend_code", "frontend_code.js", "javascript"),
    ]

    # Butuh spec dari Product Spec Agent
    required_fields = ["spec"]

    # =========================================================================
    # PROMPT BUILDING
    # =========================================================================

    def build_prompt(self, state: Dict[str, Any]) -> str:
        """
        Bangun prompt untuk implementasi frontend.

        Prompt ini berisi:
        1. Spesifikasi dari Product Spec Agent
        2. Struktur folder untuk berbagai framework
        3. Fitur wajib yang harus diimplementasikan
        """
        spec = state.get("spec", "")

        return f"""Kamu adalah Frontend Engineer Agent.

TUGAS: Implementasi frontend lengkap berdasarkan spesifikasi.

SPESIFIKASI:
{spec}

LANGKAH PERTAMA - BACA TECH STACK:
Lihat bagian tech_stack di spesifikasi untuk menentukan framework frontend:
- React, Vue, Angular, Svelte, Next.js, Nuxt, dll

STRUKTUR FILE SESUAI TECH STACK:

{_format_frontend_structures()}

FITUR WAJIB:
- UI sesuai fitur di spesifikasi
- Routing/navigation
- API integration dengan error handling
- Responsive design
- Form validation

{self.get_file_format_instructions()}

Generate setiap file secara lengkap dan siap dijalankan."""

    # =========================================================================
    # RESPONSE PROCESSING
    # =========================================================================

    def process_response(self, state: Dict[str, Any], response: Any) -> Dict[str, Any]:
        """
        Proses response dari LLM.

        Simpan hasil ke state["frontend_code"].
        """
        state["frontend_code"] = response.content
        state["status"] = "frontend_built"
        return state


# =============================================================================
# LEGACY FUNCTION (untuk backward compatibility)
# =============================================================================

_agent = FrontendAgent()


def frontend_engineer_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy function wrapper untuk backward compatibility."""
    return _agent.execute(state)
