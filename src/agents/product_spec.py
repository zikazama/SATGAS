"""
Product Spec Agent
==================

Agent kedua dalam pipeline yang bertugas:
- Mengubah prompt menjadi spesifikasi teknis (spec.yaml)
- Membuat acceptance tests (acceptance_tests.md)
- Mendefinisikan data models dan API endpoints

CUSTOMIZATION:
--------------

Untuk mengubah format spesifikasi:
1. Override build_prompt() untuk mengubah struktur spec.yaml
2. Tambah field di output_fields untuk output tambahan
3. Override process_response() untuk post-processing

"""

from typing import Dict, Any
from .base import BaseAgent


class ProductSpecAgent(BaseAgent):
    """
    Product Spec Agent - membuat spesifikasi teknis dari prompt.

    Agent ini menghasilkan:
    - spec.yaml: Spesifikasi teknis lengkap
    - acceptance_tests.md: Acceptance criteria dengan format Given-When-Then
    """

    # =========================================================================
    # METADATA
    # =========================================================================

    agent_id = "product_spec"
    agent_name = "Product Spec"
    display_name = "Product & Spec"
    step_order = 2
    description = "Membuat spesifikasi teknis"
    color = "#26A69A"

    # Output: spec.yaml dan acceptance_tests.md
    output_fields = [
        ("spec", "spec.yaml", "yaml"),
        ("acceptance_tests", "acceptance_tests.md", "markdown"),
    ]

    # Tidak butuh required fields (menggunakan prompt langsung)
    required_fields = []

    # =========================================================================
    # PROMPT BUILDING
    # =========================================================================

    def build_prompt(self, state: Dict[str, Any]) -> str:
        """
        Bangun prompt untuk membuat spesifikasi teknis.

        Prompt ini menginstruksikan LLM untuk:
        1. Menganalisis tech stack dari prompt
        2. Membuat spec.yaml dengan struktur standar
        3. Membuat acceptance tests
        """
        prompt = state["prompt"]

        return f"""Kamu adalah Product & Spec Agent.

TUGAS: Ubah prompt pengguna menjadi spesifikasi teknis dan acceptance tests.

PROMPT PENGGUNA:
{prompt}

LANGKAH PERTAMA - ANALISIS TECH STACK:
Baca prompt dengan teliti dan identifikasi teknologi yang diminta:
- Backend: Express, FastAPI, Django, Laravel, Gin, Rails, Spring Boot, dll
- Frontend: React, Vue, Angular, Svelte, Next.js, Nuxt, dll
- Database: MongoDB, PostgreSQL, MySQL, SQLite, Redis, dll
- Bahasa: JavaScript, TypeScript, Python, PHP, Go, Ruby, Java, dll

ATURAN PENTING:
- GUNAKAN PERSIS teknologi yang disebut user
- Jangan pernah mengganti ke teknologi lain
- Jika user bilang "PHP Laravel" -> gunakan Laravel
- Jika user bilang "Golang Gin" -> gunakan Gin
- Jika user bilang "Ruby Rails" -> gunakan Rails
- Jika tidak disebutkan, gunakan default yang masuk akal

FILE YANG HARUS DIBUAT:

1. docs/spec.yaml - Spesifikasi teknis:
   project_info:
     name: nama proyek
     description: deskripsi singkat
     version: "1.0.0"
   tech_stack:
     language: (bahasa pemrograman yang diminta)
     backend: (framework backend yang diminta)
     frontend: (framework frontend yang diminta)
     database: (database yang sesuai)
   scope:
     features: [daftar fitur]
     constraints: [batasan]
   data_models:
     - name: ModelName
       fields: [field1, field2]
   api_endpoints:
     - method: GET/POST/PUT/DELETE
       path: /api/...
       description: ...

2. docs/acceptance_tests.md - Acceptance criteria dengan format Given-When-Then

{self.get_file_format_instructions()}

Generate kedua file dengan lengkap."""

    # =========================================================================
    # RESPONSE PROCESSING
    # =========================================================================

    def process_response(self, state: Dict[str, Any], response: Any) -> Dict[str, Any]:
        """
        Proses response dari LLM.

        Simpan hasil ke state["spec"] dan state["acceptance_tests"].
        Keduanya diambil dari response yang sama karena LLM menggenerate
        dalam satu output.
        """
        state["spec"] = response.content
        state["acceptance_tests"] = response.content
        state["status"] = "spec_created"
        return state


# =============================================================================
# LEGACY FUNCTION (untuk backward compatibility)
# =============================================================================

_agent = ProductSpecAgent()


def product_spec_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy function wrapper untuk backward compatibility."""
    return _agent.execute(state)
