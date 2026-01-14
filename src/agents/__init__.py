"""
SATGAS Agent Module
===================

Modul ini menyediakan semua agent dan sistem registry untuk SATGAS framework.

QUICK START - Menggunakan Agent:
--------------------------------

    from src.agents import registry

    # Dapatkan semua agent terurut
    for agent in registry.get_agents():
        print(f"{agent.step_order}. {agent.agent_name}")

    # Dapatkan config untuk UI
    configs = registry.get_ui_configs()


QUICK START - Menambah Agent Baru:
----------------------------------

1. Buat file agent baru (contoh: my_agent.py)
2. Extend BaseAgent dan implementasikan method
3. Tambahkan import dan daftarkan di registry.py

Lihat dokumentasi lengkap di:
- base.py: BaseAgent class documentation
- registry.py: Registry system documentation


ARSITEKTUR:
-----------

    BaseAgent (base.py)
        │
        ├── OrchestratorAgent
        ├── ProductSpecAgent
        ├── BackendAgent
        ├── FrontendAgent
        ├── TestAgent
        ├── SecurityAgent
        ├── QAAgent
        └── DevOpsAgent
              │
              └── AgentRegistry (registry.py)
                      │
                      ├── Workflow (workflow.py)
                      ├── UI (app.py)
                      └── State (state.py)

"""

# =============================================================================
# BASE CLASS
# =============================================================================

from .base import BaseAgent

# =============================================================================
# AGENT CLASSES
# =============================================================================

from .orchestrator import OrchestratorAgent
from .product_spec import ProductSpecAgent
from .backend import BackendAgent
from .frontend import FrontendAgent
from .test import TestAgent
from .security import SecurityAgent
from .qa import QAAgent
from .devops import DevOpsAgent

# =============================================================================
# REGISTRY
# =============================================================================

from .registry import (
    registry,
    AgentRegistry,
    get_agents,
    get_agent,
    get_ui_configs,
)

# =============================================================================
# LEGACY EXPORTS (untuk backward compatibility)
# =============================================================================
# Fungsi-fungsi ini masih diexport untuk kompatibilitas dengan kode lama.
# Untuk kode baru, gunakan registry system.

from .orchestrator import orchestrator_agent
from .product_spec import product_spec_agent
from .backend import backend_engineer_agent
from .frontend import frontend_engineer_agent
from .test import test_engineer_agent
from .security import security_agent
from .qa import qa_critic_agent
from .devops import devops_agent

# =============================================================================
# PUBLIC API
# =============================================================================

__all__ = [
    # Base class
    "BaseAgent",

    # Agent classes
    "OrchestratorAgent",
    "ProductSpecAgent",
    "BackendAgent",
    "FrontendAgent",
    "TestAgent",
    "SecurityAgent",
    "QAAgent",
    "DevOpsAgent",

    # Registry
    "registry",
    "AgentRegistry",
    "get_agents",
    "get_agent",
    "get_ui_configs",

    # Legacy function exports
    "orchestrator_agent",
    "product_spec_agent",
    "backend_engineer_agent",
    "frontend_engineer_agent",
    "test_engineer_agent",
    "security_agent",
    "qa_critic_agent",
    "devops_agent",
]
