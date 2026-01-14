"""
Settings Module
===============

Konfigurasi aplikasi SATGAS. File ini berisi semua settings yang bisa
dikustomisasi melalui environment variables atau langsung di kode.

CUSTOMIZATION:
--------------

1. LLM Provider:
   - Set LLM_PROVIDER di .env: "qwen" atau "openai"
   - Untuk OpenAI, set OPENAI_API_KEY

2. Agent Config:
   - AGENTS_CONFIG digunakan untuk UI display
   - Untuk logika agent, edit file di src/agents/

3. File Output:
   - FIELD_FILE_MAP menentukan mapping state -> file
   - Tambah entry baru saat membuat output baru


ENVIRONMENT VARIABLES:
----------------------

LLM Provider:
  LLM_PROVIDER        - "qwen" atau "openai" (default: qwen)

Qwen CLI:
  QWEN_CLI_COMMAND    - Command untuk Qwen CLI (default: qwen)
  QWEN_MODEL          - Model name (optional)
  QWEN_TIMEOUT        - Timeout dalam detik, 0=unlimited (default: 0)

OpenAI API:
  OPENAI_API_KEY      - API key (required untuk openai provider)
  OPENAI_MODEL        - Model name (default: gpt-4o-mini)
  OPENAI_TEMPERATURE  - Creativity 0.0-2.0 (default: 0.7)
  OPENAI_MAX_TOKENS   - Max tokens (default: 4096)
  OPENAI_BASE_URL     - Custom endpoint (optional)

"""

import os
from pathlib import Path

from dotenv import load_dotenv

# =============================================================================
# LOAD ENVIRONMENT
# =============================================================================

load_dotenv()

# =============================================================================
# PATH CONFIGURATION
# =============================================================================

# Root directory (satgas/)
BASE_DIR = Path(__file__).resolve().parent.parent

# Output directory untuk generated projects
PROJECTS_DIR = BASE_DIR / "projects"

# =============================================================================
# LLM PROVIDER CONFIGURATION
# =============================================================================
# Pilih provider: "qwen" (local CLI) atau "openai" (API)

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "qwen")

# -----------------------------------------------------------------------------
# Qwen CLI Settings
# -----------------------------------------------------------------------------
# Gunakan ini untuk inference dengan Qwen CLI lokal

QWEN_CLI_COMMAND = os.getenv("QWEN_CLI_COMMAND", "qwen")
QWEN_MODEL = os.getenv("QWEN_MODEL")
QWEN_TIMEOUT = int(os.getenv("QWEN_TIMEOUT", "0"))  # 0 = wait indefinitely

# -----------------------------------------------------------------------------
# OpenAI API Settings
# -----------------------------------------------------------------------------
# Gunakan ini untuk inference dengan OpenAI API atau compatible endpoint

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "4096"))
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")  # For Azure, Together AI, etc.

# =============================================================================
# TECH STACK CONFIGURATION
# =============================================================================
# Konfigurasi tech stack yang didukung oleh SATGAS.
# Tambahkan tech stack baru di sini untuk mendukung framework/bahasa baru.
#
# CARA MENAMBAH TECH STACK BARU:
# 1. Tambah entry baru di dictionary yang sesuai (BACKEND_STACKS/FRONTEND_STACKS/DATABASE_STACKS)
# 2. Ikuti format yang sudah ada
# 3. Agent akan otomatis menggunakan konfigurasi ini
#
# FORMAT BACKEND_STACKS:
# - name: Nama untuk display
# - language: Bahasa pemrograman
# - docker_image: Base image Docker
# - structure: List file/folder yang harus di-generate
# - commands: Commands untuk install, test, build, start
#
# FORMAT FRONTEND_STACKS:
# - name: Nama untuk display
# - language: Bahasa pemrograman
# - docker_image: Base image Docker
# - structure: List file/folder yang harus di-generate
# - commands: Commands untuk install, test, build, start
#
# FORMAT DATABASE_STACKS:
# - name: Nama untuk display
# - docker_image: Base image Docker
# - default_port: Port default
# - env_vars: Environment variables untuk docker-compose

BACKEND_STACKS = {
    "express": {
        "name": "Express.js",
        "language": "javascript",
        "docker_image": "node:alpine",
        "structure": [
            "backend/package.json",
            "backend/src/index.js",
            "backend/src/routes/",
            "backend/src/controllers/",
            "backend/src/models/",
            "backend/src/middleware/",
        ],
        "commands": {
            "install": "npm install",
            "test": "npm test",
            "build": "npm run build",
            "start": "npm start",
        },
    },
    "fastapi": {
        "name": "FastAPI",
        "language": "python",
        "docker_image": "python:slim",
        "structure": [
            "backend/requirements.txt",
            "backend/app/main.py",
            "backend/app/routers/",
            "backend/app/models/",
            "backend/app/schemas/",
            "backend/app/core/",
        ],
        "commands": {
            "install": "pip install -r requirements.txt",
            "test": "pytest",
            "build": "echo 'No build step'",
            "start": "uvicorn app.main:app --reload",
        },
    },
    "django": {
        "name": "Django",
        "language": "python",
        "docker_image": "python:slim",
        "structure": [
            "backend/requirements.txt",
            "backend/manage.py",
            "backend/config/settings.py",
            "backend/config/urls.py",
            "backend/apps/",
        ],
        "commands": {
            "install": "pip install -r requirements.txt",
            "test": "python manage.py test",
            "build": "python manage.py collectstatic",
            "start": "python manage.py runserver",
        },
    },
    "laravel": {
        "name": "Laravel",
        "language": "php",
        "docker_image": "php:fpm-alpine",
        "structure": [
            "backend/composer.json",
            "backend/routes/api.php",
            "backend/routes/web.php",
            "backend/app/Http/Controllers/",
            "backend/app/Models/",
            "backend/database/migrations/",
        ],
        "commands": {
            "install": "composer install",
            "test": "php artisan test",
            "build": "php artisan optimize",
            "start": "php artisan serve",
        },
    },
    "gin": {
        "name": "Gin (Go)",
        "language": "go",
        "docker_image": "golang:alpine",
        "structure": [
            "backend/go.mod",
            "backend/main.go",
            "backend/handlers/",
            "backend/models/",
            "backend/routes/",
            "backend/middleware/",
        ],
        "commands": {
            "install": "go mod download",
            "test": "go test ./...",
            "build": "go build -o main .",
            "start": "./main",
        },
    },
    "rails": {
        "name": "Ruby on Rails",
        "language": "ruby",
        "docker_image": "ruby:slim",
        "structure": [
            "backend/Gemfile",
            "backend/config/routes.rb",
            "backend/app/controllers/",
            "backend/app/models/",
            "backend/db/migrate/",
        ],
        "commands": {
            "install": "bundle install",
            "test": "rails test",
            "build": "rails assets:precompile",
            "start": "rails server",
        },
    },
    "spring": {
        "name": "Spring Boot",
        "language": "java",
        "docker_image": "eclipse-temurin:alpine",
        "structure": [
            "backend/pom.xml",
            "backend/src/main/java/com/app/Application.java",
            "backend/src/main/java/com/app/controller/",
            "backend/src/main/java/com/app/model/",
            "backend/src/main/java/com/app/repository/",
            "backend/src/main/java/com/app/service/",
        ],
        "commands": {
            "install": "mvn install",
            "test": "mvn test",
            "build": "mvn package",
            "start": "java -jar target/*.jar",
        },
    },
    "flask": {
        "name": "Flask",
        "language": "python",
        "docker_image": "python:slim",
        "structure": [
            "backend/requirements.txt",
            "backend/app/__init__.py",
            "backend/app/routes/",
            "backend/app/models/",
            "backend/run.py",
        ],
        "commands": {
            "install": "pip install -r requirements.txt",
            "test": "pytest",
            "build": "echo 'No build step'",
            "start": "flask run",
        },
    },
    "nestjs": {
        "name": "NestJS",
        "language": "typescript",
        "docker_image": "node:alpine",
        "structure": [
            "backend/package.json",
            "backend/src/main.ts",
            "backend/src/app.module.ts",
            "backend/src/controllers/",
            "backend/src/services/",
            "backend/src/entities/",
        ],
        "commands": {
            "install": "npm install",
            "test": "npm run test",
            "build": "npm run build",
            "start": "npm run start:prod",
        },
    },
    "hapi": {
        "name": "Hapi.js",
        "language": "javascript",
        "docker_image": "node:alpine",
        "structure": [
            "backend/package.json",
            "backend/src/server.js",
            "backend/src/routes/",
            "backend/src/handlers/",
            "backend/src/models/",
        ],
        "commands": {
            "install": "npm install",
            "test": "npm test",
            "build": "npm run build",
            "start": "npm start",
        },
    },
    "koa": {
        "name": "Koa.js",
        "language": "javascript",
        "docker_image": "node:alpine",
        "structure": [
            "backend/package.json",
            "backend/src/app.js",
            "backend/src/routes/",
            "backend/src/controllers/",
            "backend/src/models/",
        ],
        "commands": {
            "install": "npm install",
            "test": "npm test",
            "build": "npm run build",
            "start": "npm start",
        },
    },
}

FRONTEND_STACKS = {
    "react": {
        "name": "React",
        "language": "javascript",
        "docker_image": "node:alpine",
        "structure": [
            "frontend/package.json",
            "frontend/src/index.js",
            "frontend/src/App.jsx",
            "frontend/src/components/",
            "frontend/src/pages/",
            "frontend/src/hooks/",
            "frontend/src/services/",
        ],
        "commands": {
            "install": "npm install",
            "test": "npm test",
            "build": "npm run build",
            "start": "npm start",
        },
    },
    "vue": {
        "name": "Vue.js",
        "language": "javascript",
        "docker_image": "node:alpine",
        "structure": [
            "frontend/package.json",
            "frontend/src/main.js",
            "frontend/src/App.vue",
            "frontend/src/components/",
            "frontend/src/views/",
            "frontend/src/composables/",
            "frontend/src/services/",
        ],
        "commands": {
            "install": "npm install",
            "test": "npm run test",
            "build": "npm run build",
            "start": "npm run serve",
        },
    },
    "angular": {
        "name": "Angular",
        "language": "typescript",
        "docker_image": "node:alpine",
        "structure": [
            "frontend/package.json",
            "frontend/src/main.ts",
            "frontend/src/app/app.component.ts",
            "frontend/src/app/app.module.ts",
            "frontend/src/app/components/",
            "frontend/src/app/services/",
        ],
        "commands": {
            "install": "npm install",
            "test": "ng test",
            "build": "ng build",
            "start": "ng serve",
        },
    },
    "svelte": {
        "name": "Svelte",
        "language": "javascript",
        "docker_image": "node:alpine",
        "structure": [
            "frontend/package.json",
            "frontend/src/main.js",
            "frontend/src/App.svelte",
            "frontend/src/lib/",
            "frontend/src/routes/",
        ],
        "commands": {
            "install": "npm install",
            "test": "npm run test",
            "build": "npm run build",
            "start": "npm run dev",
        },
    },
    "nextjs": {
        "name": "Next.js",
        "language": "javascript",
        "docker_image": "node:alpine",
        "structure": [
            "frontend/package.json",
            "frontend/pages/_app.js",
            "frontend/pages/index.js",
            "frontend/components/",
            "frontend/lib/",
            "frontend/styles/",
        ],
        "commands": {
            "install": "npm install",
            "test": "npm run test",
            "build": "npm run build",
            "start": "npm run start",
        },
    },
    "nuxt": {
        "name": "Nuxt",
        "language": "javascript",
        "docker_image": "node:alpine",
        "structure": [
            "frontend/package.json",
            "frontend/nuxt.config.js",
            "frontend/pages/index.vue",
            "frontend/components/",
            "frontend/composables/",
        ],
        "commands": {
            "install": "npm install",
            "test": "npm run test",
            "build": "npm run build",
            "start": "npm run start",
        },
    },
    "blade": {
        "name": "Blade (Laravel)",
        "language": "php",
        "docker_image": "php:fpm-alpine",
        "structure": [
            "resources/views/layouts/app.blade.php",
            "resources/views/components/",
            "resources/views/pages/",
            "resources/css/app.css",
            "resources/js/app.js",
        ],
        "commands": {
            "install": "npm install",
            "test": "npm run test",
            "build": "npm run build",
            "start": "npm run dev",
        },
    },
    "ejs": {
        "name": "EJS",
        "language": "javascript",
        "docker_image": "node:alpine",
        "structure": [
            "views/layouts/main.ejs",
            "views/partials/",
            "views/pages/",
            "public/css/",
            "public/js/",
        ],
        "commands": {
            "install": "npm install",
            "test": "npm test",
            "build": "echo 'No build step'",
            "start": "npm start",
        },
    },
    "thymeleaf": {
        "name": "Thymeleaf",
        "language": "java",
        "docker_image": "eclipse-temurin:alpine",
        "structure": [
            "src/main/resources/templates/",
            "src/main/resources/static/css/",
            "src/main/resources/static/js/",
        ],
        "commands": {
            "install": "mvn install",
            "test": "mvn test",
            "build": "mvn package",
            "start": "java -jar target/*.jar",
        },
    },
}

DATABASE_STACKS = {
    "postgresql": {
        "name": "PostgreSQL",
        "docker_image": "postgres:alpine",
        "default_port": 5432,
        "env_vars": {
            "POSTGRES_USER": "${DB_USER:-postgres}",
            "POSTGRES_PASSWORD": "${DB_PASSWORD:-postgres}",
            "POSTGRES_DB": "${DB_NAME:-app}",
        },
    },
    "mysql": {
        "name": "MySQL",
        "docker_image": "mysql:8",
        "default_port": 3306,
        "env_vars": {
            "MYSQL_ROOT_PASSWORD": "${DB_ROOT_PASSWORD:-root}",
            "MYSQL_USER": "${DB_USER:-app}",
            "MYSQL_PASSWORD": "${DB_PASSWORD:-app}",
            "MYSQL_DATABASE": "${DB_NAME:-app}",
        },
    },
    "mongodb": {
        "name": "MongoDB",
        "docker_image": "mongo:latest",
        "default_port": 27017,
        "env_vars": {
            "MONGO_INITDB_ROOT_USERNAME": "${DB_USER:-root}",
            "MONGO_INITDB_ROOT_PASSWORD": "${DB_PASSWORD:-root}",
            "MONGO_INITDB_DATABASE": "${DB_NAME:-app}",
        },
    },
    "sqlite": {
        "name": "SQLite",
        "docker_image": None,  # No container needed
        "default_port": None,
        "env_vars": {},
    },
    "redis": {
        "name": "Redis",
        "docker_image": "redis:alpine",
        "default_port": 6379,
        "env_vars": {},
    },
    "mariadb": {
        "name": "MariaDB",
        "docker_image": "mariadb:latest",
        "default_port": 3306,
        "env_vars": {
            "MARIADB_ROOT_PASSWORD": "${DB_ROOT_PASSWORD:-root}",
            "MARIADB_USER": "${DB_USER:-app}",
            "MARIADB_PASSWORD": "${DB_PASSWORD:-app}",
            "MARIADB_DATABASE": "${DB_NAME:-app}",
        },
    },
    "cassandra": {
        "name": "Cassandra",
        "docker_image": "cassandra:latest",
        "default_port": 9042,
        "env_vars": {},
    },
    "elasticsearch": {
        "name": "Elasticsearch",
        "docker_image": "elasticsearch:8.11.0",
        "default_port": 9200,
        "env_vars": {
            "discovery.type": "single-node",
            "xpack.security.enabled": "false",
        },
    },
}


# =============================================================================
# HELPER FUNCTIONS FOR TECH STACKS
# =============================================================================

def get_backend_names() -> list:
    """Dapatkan list nama backend frameworks."""
    return [stack["name"] for stack in BACKEND_STACKS.values()]


def get_frontend_names() -> list:
    """Dapatkan list nama frontend frameworks."""
    return [stack["name"] for stack in FRONTEND_STACKS.values()]


def get_database_names() -> list:
    """Dapatkan list nama databases."""
    return [stack["name"] for stack in DATABASE_STACKS.values()]


def get_backend_by_keyword(keyword: str) -> dict:
    """
    Cari backend stack berdasarkan keyword.

    Args:
        keyword: Kata kunci (case insensitive)

    Returns:
        Dict config atau None jika tidak ditemukan
    """
    keyword = keyword.lower()
    for key, stack in BACKEND_STACKS.items():
        if keyword in key or keyword in stack["name"].lower():
            return stack
    return None


def get_frontend_by_keyword(keyword: str) -> dict:
    """
    Cari frontend stack berdasarkan keyword.

    Args:
        keyword: Kata kunci (case insensitive)

    Returns:
        Dict config atau None jika tidak ditemukan
    """
    keyword = keyword.lower()
    for key, stack in FRONTEND_STACKS.items():
        if keyword in key or keyword in stack["name"].lower():
            return stack
    return None


def get_database_by_keyword(keyword: str) -> dict:
    """
    Cari database stack berdasarkan keyword.

    Args:
        keyword: Kata kunci (case insensitive)

    Returns:
        Dict config atau None jika tidak ditemukan
    """
    keyword = keyword.lower()
    for key, stack in DATABASE_STACKS.items():
        if keyword in key or keyword in stack["name"].lower():
            return stack
    return None


def format_tech_stack_list() -> str:
    """
    Format daftar tech stack untuk prompt LLM.

    Returns:
        String berisi daftar tech stack yang terformat
    """
    backends = ", ".join(get_backend_names())
    frontends = ", ".join(get_frontend_names())
    databases = ", ".join(get_database_names())

    return f"""- Backend: {backends}
- Frontend: {frontends}
- Database: {databases}"""


# =============================================================================
# AGENT CONFIGURATION (UI)
# =============================================================================
# Config ini digunakan untuk display di UI.
# Untuk logika agent, lihat src/agents/*.py
#
# CATATAN: Dengan framework baru, config ini bisa di-generate otomatis
# dari registry menggunakan registry.get_ui_configs().
# Config manual ini dipertahankan untuk backward compatibility.
#
# FORMAT:
# - id: Agent ID (harus match dengan agent_id di class)
# - name: Nama untuk display
# - step: Urutan eksekusi (1-based)
# - color: Warna hex untuk UI
# - description: Deskripsi singkat
# - outputs: List of (state_key, filename, language)

# Tactical Theme Colors for Agents
# Primary: #4BA91C (Tactical Green), #356D21 (Deep Tactical Green)
# Accent: #6BE31E (Neon Vision Green), #A7E55B (Lime Highlight)
# Secondary: #30353A (Gunmetal), #9EA7A6 (Steel Gray)

AGENTS_CONFIG = [
    {
        "id": "orchestrator",
        "name": "Orchestrator",
        "step": 1,
        "color": "#6BE31E",  # Neon Vision Green - command center
        "description": "Mengatur workflow dan prioritas",
        "outputs": [("tasks", "tasks.json", "json")]
    },
    {
        "id": "product_spec",
        "name": "Product Spec",
        "step": 2,
        "color": "#4BA91C",  # Tactical Green - planning
        "description": "Membuat spesifikasi teknis",
        "outputs": [
            ("spec", "spec.yaml", "yaml"),
            ("acceptance_tests", "acceptance_tests.md", "markdown")
        ]
    },
    {
        "id": "backend",
        "name": "Backend",
        "step": 3,
        "color": "#356D21",  # Deep Tactical Green - core systems
        "description": "Implementasi backend dan API",
        "outputs": [("backend_code", "backend_code.py", "python")]
    },
    {
        "id": "frontend",
        "name": "Frontend",
        "step": 4,
        "color": "#A7E55B",  # Lime Highlight - user interface
        "description": "Implementasi UI dan UX",
        "outputs": [("frontend_code", "frontend_code.js", "javascript")]
    },
    {
        "id": "test",
        "name": "Testing",
        "step": 5,
        "color": "#4BA91C",  # Tactical Green - verification
        "description": "Membuat test suites",
        "outputs": [("test_plan", "test_plan.md", "markdown")]
    },
    {
        "id": "security",
        "name": "Security",
        "step": 6,
        "color": "#356D21",  # Deep Tactical Green - protection
        "description": "Threat modeling dan security checks",
        "outputs": [
            ("threat_model", "threat_model.md", "markdown"),
            ("security_requirements", "security_requirements.md", "markdown"),
            ("security_findings", "security_findings.json", "json")
        ]
    },
    {
        "id": "qa",
        "name": "QA Review",
        "step": 7,
        "color": "#A7E55B",  # Lime Highlight - quality check
        "description": "Review kode dan quality assurance",
        "outputs": [("qa_findings", "qa_findings.json", "json")]
    },
    {
        "id": "devops",
        "name": "DevOps",
        "step": 8,
        "color": "#6BE31E",  # Neon Vision Green - deployment
        "description": "Docker, CI/CD, dan deployment",
        "outputs": [
            ("docker_compose", "docker-compose.yml", "yaml"),
            ("ci_config", "ci-config.yml", "yaml"),
            ("runbook", "runbook.md", "markdown")
        ]
    }
]

# =============================================================================
# FILE PERSISTENCE MAPPING
# =============================================================================
# Mapping dari state field ke filename untuk file persistence.
# Format: (state_key, filename)
#
# CARA MENAMBAH:
# 1. Tambah entry baru di list ini
# 2. Pastikan agent mengisi state_key yang sesuai
# 3. File akan otomatis tersimpan

FIELD_FILE_MAP = [
    ("prompt", "prompt.txt"),
    ("tasks", "tasks.json"),
    ("spec", "spec.yaml"),
    ("acceptance_tests", "acceptance_tests.md"),
    ("backend_code", "backend_code.py"),
    ("frontend_code", "frontend_code.js"),
    ("qa_findings", "qa_findings.json"),
    ("test_plan", "test_plan.md"),
    ("threat_model", "threat_model.md"),
    ("security_requirements", "security_requirements.md"),
    ("security_findings", "security_findings.json"),
    ("docker_compose", "docker-compose.yml"),
    ("ci_config", "ci-config.yml"),
    ("runbook", "runbook.md"),
    ("status", "status.txt"),
]

# =============================================================================
# UI CONFIGURATION
# =============================================================================

# Placeholder text untuk input prompt
PLACEHOLDER_EXAMPLE = """Contoh: Buatkan aplikasi manajemen inventaris untuk toko kelontong. Fitur utama: login admin, CRUD produk (nama, harga, stok, kategori), notifikasi stok rendah, laporan penjualan harian/bulanan, dan dashboard statistik. Gunakan React untuk frontend dan FastAPI untuk backend dengan database PostgreSQL."""

# =============================================================================
# SETTINGS CLASS
# =============================================================================
# Container class untuk akses settings.
# Import: from config.settings import SETTINGS


class Settings:
    """
    Application settings container.

    Usage:
        from config.settings import SETTINGS

        print(SETTINGS.LLM_PROVIDER)
        print(SETTINGS.PROJECTS_DIR)
    """

    # Paths
    BASE_DIR = BASE_DIR
    PROJECTS_DIR = PROJECTS_DIR

    # LLM Provider
    LLM_PROVIDER = LLM_PROVIDER

    # Qwen Settings
    QWEN_CLI_COMMAND = QWEN_CLI_COMMAND
    QWEN_MODEL = QWEN_MODEL
    QWEN_TIMEOUT = QWEN_TIMEOUT

    # OpenAI Settings
    OPENAI_API_KEY = OPENAI_API_KEY
    OPENAI_MODEL = OPENAI_MODEL
    OPENAI_TEMPERATURE = OPENAI_TEMPERATURE
    OPENAI_MAX_TOKENS = OPENAI_MAX_TOKENS
    OPENAI_BASE_URL = OPENAI_BASE_URL

    # Agent & File Config
    AGENTS_CONFIG = AGENTS_CONFIG
    FIELD_FILE_MAP = FIELD_FILE_MAP
    PLACEHOLDER_EXAMPLE = PLACEHOLDER_EXAMPLE

    # Tech Stack Config
    BACKEND_STACKS = BACKEND_STACKS
    FRONTEND_STACKS = FRONTEND_STACKS
    DATABASE_STACKS = DATABASE_STACKS

    # Tech Stack Helper Methods
    @staticmethod
    def get_backend_names():
        return get_backend_names()

    @staticmethod
    def get_frontend_names():
        return get_frontend_names()

    @staticmethod
    def get_database_names():
        return get_database_names()

    @staticmethod
    def get_backend_by_keyword(keyword: str):
        return get_backend_by_keyword(keyword)

    @staticmethod
    def get_frontend_by_keyword(keyword: str):
        return get_frontend_by_keyword(keyword)

    @staticmethod
    def get_database_by_keyword(keyword: str):
        return get_database_by_keyword(keyword)

    @staticmethod
    def format_tech_stack_list():
        return format_tech_stack_list()


# Global settings instance
SETTINGS = Settings()
