"""
Backend Agent
=============

Agent ketiga dalam pipeline yang bertugas:
- Implementasi backend sesuai tech stack di spec
- Membuat struktur folder sesuai framework
- Implementasi CRUD, auth, validation, dan error handling

CUSTOMIZATION:
--------------

Untuk menambah dukungan tech stack baru:
1. Tambahkan entry di BACKEND_STACKS di config/settings.py
2. Agent akan otomatis menggunakan struktur yang didefinisikan

"""

from typing import Dict, Any
from .base import BaseAgent
from config.settings import BACKEND_STACKS


def _format_backend_structures() -> str:
    """Format struktur file dari BACKEND_STACKS untuk prompt."""
    lines = []
    for key, stack in BACKEND_STACKS.items():
        name = stack["name"]
        structure = ", ".join(stack["structure"])
        lines.append(f"{name}:\n- {structure}")
    return "\n\n".join(lines)


class BackendAgent(BaseAgent):
    """
    Backend Agent - implementasi backend berdasarkan spesifikasi.

    Agent ini menghasilkan file backend sesuai tech stack:
    - Express.js: package.json, src/index.js, routes, controllers, models
    - FastAPI: requirements.txt, app/main.py, routers, models, schemas
    - Laravel: composer.json, routes/api.php, Controllers, Models
    - Dan framework lainnya
    """

    # =========================================================================
    # METADATA
    # =========================================================================

    agent_id = "backend"
    agent_name = "Backend"
    display_name = "Backend Engineer"
    step_order = 3
    description = "Implementasi backend dan API"
    color = "#42A5F5"

    # Output: backend code (semua file backend dalam satu output)
    output_fields = [
        ("backend_code", "backend_code.py", "python"),
    ]

    # Butuh spec dari Product Spec Agent
    required_fields = ["spec"]

    # =========================================================================
    # PROMPT BUILDING
    # =========================================================================

    def build_prompt(self, state: Dict[str, Any]) -> str:
        """
        Bangun prompt untuk implementasi backend.

        Prompt ini berisi:
        1. Spesifikasi dari Product Spec Agent
        2. Struktur folder untuk berbagai tech stack
        3. Fitur wajib yang harus diimplementasikan
        """
        spec = state.get("spec", "")

        return f"""Kamu adalah Backend Engineer Agent.

TUGAS: Implementasi backend lengkap berdasarkan spesifikasi.

SPESIFIKASI:
{spec}

LANGKAH PERTAMA - BACA TECH STACK:
Lihat bagian tech_stack di spesifikasi untuk menentukan:
- Bahasa pemrograman (JavaScript, Python, PHP, Go, Ruby, Java, dll)
- Framework backend (Express, FastAPI, Laravel, Gin, Rails, Spring Boot, dll)
- Database (MongoDB, PostgreSQL, MySQL, dll)

STRUKTUR FILE SESUAI TECH STACK:

{_format_backend_structures()}

FITUR WAJIB:
- CRUD operations sesuai data_models di spesifikasi
- API endpoints sesuai api_endpoints di spesifikasi
- Input validation
- Error handling yang konsisten
- Database integration sesuai tech_stack

{self.get_file_format_instructions()}

Generate setiap file secara lengkap dan siap dijalankan."""

    # =========================================================================
    # RESPONSE PROCESSING
    # =========================================================================

    def process_response(self, state: Dict[str, Any], response: Any) -> Dict[str, Any]:
        """
        Proses response dari LLM.

        Simpan hasil ke state["backend_code"].
        """
        state["backend_code"] = response.content
        state["status"] = "backend_built"
        return state


# =============================================================================
# LEGACY FUNCTION (untuk backward compatibility)
# =============================================================================

_agent = BackendAgent()


def backend_engineer_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy function wrapper untuk backward compatibility."""
    return _agent.execute(state)
