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

###############################################################################
# ATURAN DOCKERFILE (SANGAT PENTING):
###############################################################################

SEMUA KOMENTAR DI DOCKERFILE HARUS DIAWALI DENGAN '#':

SALAH (tidak akan ter-highlight sebagai komentar):
```dockerfile
FROM python:3.11-slim
Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
Expose port
EXPOSE 8000
```

BENAR (komentar akan ter-highlight dengan benar):
```dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1

# Expose port
EXPOSE 8000
```

TEMPLATE DOCKERFILE PYTHON/FASTAPI:
```dockerfile
FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    PYTHONPATH=/app

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    gcc \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \\
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM base AS production

# Copy application code
COPY . .

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

TEMPLATE DOCKERFILE NODE.JS:
```dockerfile
FROM node:20-alpine AS base

# Set working directory
WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci --only=production

# Production stage
FROM base AS production

# Copy application code
COPY . .

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \\
    adduser -S nextjs -u 1001

# Switch to non-root user
USER nextjs

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \\
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/health || exit 1

# Run the application
CMD ["node", "dist/index.js"]
```

CHECKLIST DOCKERFILE:
[x] Setiap komentar HARUS diawali dengan '# ' (hash + spasi)
[x] Gunakan multi-stage build untuk production
[x] Jalankan sebagai non-root user
[x] Tambahkan health check
[x] Gunakan --no-install-recommends untuk apt-get

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
