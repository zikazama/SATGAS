"""
DevOps Agent
============

Agent kedelapan (terakhir) dalam pipeline yang bertugas:
- Membuat Dockerfile untuk backend dan frontend
- Membuat docker-compose.yml
- Membuat CI/CD pipeline (.github/workflows/ci.yml)
- Membuat runbook untuk operations

CUSTOMIZATION:
--------------

Untuk menambah dukungan tech stack baru:
1. Tambahkan entry di config/settings.py (BACKEND_STACKS, FRONTEND_STACKS, DATABASE_STACKS)
2. Agent akan otomatis menggunakan docker_image dan commands dari konfigurasi

"""

from typing import Dict, Any
from .base import BaseAgent
from config.settings import BACKEND_STACKS, FRONTEND_STACKS, DATABASE_STACKS


def _format_docker_images() -> str:
    """Format Docker images dari tech stack config untuk prompt."""
    # Backend images
    backend_lines = ["Backend:"]
    for key, stack in BACKEND_STACKS.items():
        backend_lines.append(f"- {stack['name']} -> {stack['docker_image']}")

    # Database images
    db_lines = ["\nDatabase:"]
    for key, stack in DATABASE_STACKS.items():
        if stack["docker_image"]:
            db_lines.append(f"- {stack['name']} -> {stack['docker_image']}")

    return "\n".join(backend_lines + db_lines)


def _format_ci_commands() -> str:
    """Format CI/CD commands dari tech stack config untuk prompt."""
    lines = []
    for key, stack in BACKEND_STACKS.items():
        cmds = stack["commands"]
        lines.append(f"- {stack['name']}: {cmds['install']}, {cmds['test']}, {cmds['build']}")
    return "\n".join(lines)


class DevOpsAgent(BaseAgent):
    """
    DevOps Agent - membuat konfigurasi deployment dan CI/CD.

    Agent ini menghasilkan:
    - docker-compose.yml: Multi-service configuration
    - ci-config.yml: GitHub Actions workflow
    - runbook.md: Operations guide
    """

    # =========================================================================
    # METADATA
    # =========================================================================

    agent_id = "devops"
    agent_name = "DevOps"
    display_name = "DevOps"
    step_order = 8
    description = "Docker, CI/CD, dan deployment"
    color = "#78909C"

    # Output: DevOps configuration files
    output_fields = [
        ("docker_compose", "docker-compose.yml", "yaml"),
        ("ci_config", "ci-config.yml", "yaml"),
        ("runbook", "runbook.md", "markdown"),
    ]

    # Butuh spec untuk menentukan tech stack
    required_fields = ["spec"]

    # =========================================================================
    # PROMPT BUILDING
    # =========================================================================

    def build_prompt(self, state: Dict[str, Any]) -> str:
        """
        Bangun prompt untuk DevOps configuration.

        Prompt ini berisi:
        1. Spec dengan tech stack info
        2. Template Docker untuk berbagai bahasa
        3. CI/CD commands per tech stack
        """
        spec = state.get("spec", "")[:1500]

        return f"""Kamu adalah DevOps Agent.

TUGAS: Buat konfigurasi Docker, CI/CD, dan Runbook sesuai tech stack.

SPESIFIKASI:
{spec}

LANGKAH PERTAMA - BACA TECH STACK:
Lihat spesifikasi untuk menentukan base image dan commands yang sesuai:

Docker Base Images:
{_format_docker_images()}

FILE YANG HARUS DIBUAT:

1. backend/Dockerfile - Multi-stage build sesuai bahasa
2. frontend/Dockerfile - Sesuai frontend framework (node untuk SPA, atau skip jika SSR/Laravel)
3. docker-compose.yml - Services: backend, frontend (jika terpisah), database
4. .github/workflows/ci.yml - CI/CD dengan commands sesuai bahasa:
{_format_ci_commands()}
5. docs/RUNBOOK.md - Operations guide

REQUIREMENTS:
- Dockerfile dengan non-root user dan health check
- docker-compose dengan environment variables
- CI pipeline: lint, test, build

{self.get_file_format_instructions()}

Generate setiap file secara lengkap."""

    # =========================================================================
    # RESPONSE PROCESSING
    # =========================================================================

    def process_response(self, state: Dict[str, Any], response: Any) -> Dict[str, Any]:
        """
        Proses response dari LLM.

        Simpan ke 3 state fields karena LLM menggenerate semua
        file dalam satu output.
        """
        state["docker_compose"] = response.content
        state["ci_config"] = response.content
        state["runbook"] = response.content
        state["status"] = "devops_done"
        return state


# =============================================================================
# LEGACY FUNCTION (untuk backward compatibility)
# =============================================================================

_agent = DevOpsAgent()


def devops_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy function wrapper untuk backward compatibility."""
    return _agent.execute(state)
