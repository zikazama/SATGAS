"""
Orchestrator Agent
==================

Agent pertama dalam pipeline yang bertugas:
- Menganalisis prompt pengguna
- Mengidentifikasi tech stack yang diminta
- Membuat project plan (tasks.json)
- Menentukan workflow eksekusi agent selanjutnya

CUSTOMIZATION:
--------------

Untuk mengubah behavior orchestrator:
1. Override build_prompt() untuk mengubah cara analisis prompt
2. Override process_response() untuk mengubah format output
3. Ubah output_fields untuk menambah file output baru

Tech stack yang didukung dikonfigurasi di config/settings.py:
- BACKEND_STACKS: Daftar backend frameworks
- FRONTEND_STACKS: Daftar frontend frameworks
- DATABASE_STACKS: Daftar database systems

"""

from typing import Dict, Any
from .base import BaseAgent
from config.settings import format_tech_stack_list


class OrchestratorAgent(BaseAgent):
    """
    Orchestrator Agent - menganalisis prompt dan membuat project plan.

    Agent ini adalah entry point dari pipeline. Tugasnya:
    - Parse prompt pengguna untuk mengekstrak requirements
    - Identifikasi tech stack (backend, frontend, database, bahasa)
    - Generate tasks.json berisi project plan
    """

    # =========================================================================
    # METADATA
    # =========================================================================

    agent_id = "orchestrator"
    agent_name = "Orchestrator"
    display_name = "Orchestrator"
    step_order = 1
    description = "Mengatur workflow dan prioritas"
    color = "#5C6BC0"

    # Output: tasks.json berisi project plan
    output_fields = [
        ("tasks", "tasks.json", "json"),
    ]

    # Tidak butuh input dari agent lain (agent pertama)
    required_fields = []

    # =========================================================================
    # PROMPT BUILDING
    # =========================================================================

    def build_prompt(self, state: Dict[str, Any]) -> str:
        """
        Bangun prompt untuk menganalisis user input.

        Prompt ini menginstruksikan LLM untuk:
        1. Mengidentifikasi tech stack dari prompt
        2. Membuat project plan dalam format JSON
        """
        prompt = state["prompt"]

        return f"""Kamu adalah Orchestrator Agent untuk membangun aplikasi fullstack.

TUGAS UTAMA:
Analisis prompt pengguna dengan teliti dan identifikasi SEMUA teknologi yang diminta.

PROMPT PENGGUNA:
{prompt}

LANGKAH 1 - IDENTIFIKASI TECH STACK:
Baca prompt dan cari kata kunci teknologi:
{format_tech_stack_list()}
- Bahasa: JavaScript, TypeScript, Python, PHP, Go, Ruby, Java, Kotlin, Rust, dll

ATURAN PENTING:
- GUNAKAN PERSIS teknologi yang disebut user dalam prompt
- Jangan pernah mengganti ke teknologi lain
- Jika tidak disebutkan, gunakan default yang masuk akal berdasarkan konteks

FILE YANG HARUS DIBUAT:

1. docs/tasks.json - Project plan:
{{
  "project_name": "nama proyek dari prompt",
  "tech_stack": {{
    "language": "bahasa pemrograman yang diminta",
    "backend": "framework backend yang diminta",
    "frontend": "framework frontend yang diminta",
    "database": "database yang sesuai"
  }},
  "milestones": [
    {{"id": 1, "name": "Setup", "tasks": ["..."]}}
  ],
  "workflow": ["spec", "backend", "frontend", "test", "security", "qa", "devops"],
  "summary": "ringkasan proyek"
}}

{self.get_file_format_instructions()}

Generate file dengan lengkap."""

    # =========================================================================
    # RESPONSE PROCESSING
    # =========================================================================

    def process_response(self, state: Dict[str, Any], response: Any) -> Dict[str, Any]:
        """
        Proses response dari LLM.

        Simpan hasil ke state["tasks"] yang akan digunakan
        oleh agent selanjutnya.
        """
        state["tasks"] = response.content
        state["status"] = "orchestrated"
        return state


# =============================================================================
# LEGACY FUNCTION (untuk backward compatibility)
# =============================================================================

# Instance global untuk digunakan langsung
_agent = OrchestratorAgent()


def orchestrator_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy function wrapper untuk backward compatibility."""
    return _agent.execute(state)
