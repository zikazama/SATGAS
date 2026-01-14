"""
Agent Registry Module
=====================

Modul ini mengelola registrasi dan discovery semua agent dalam SATGAS.
Registry memungkinkan penambahan/penghapusan agent secara plug-and-play.

CARA MENAMBAH AGENT BARU:
-------------------------

1. Buat agent class yang extend BaseAgent (lihat base.py)

2. Import agent class di sini:

   from .my_agent import MyAgent

3. Tambahkan ke list AGENT_CLASSES:

   AGENT_CLASSES: List[Type[BaseAgent]] = [
       OrchestratorAgent,
       ProductSpecAgent,
       ...
       MyAgent,  # <-- Tambahkan di sini
   ]

4. Done! Agent akan otomatis:
   - Terdaftar di workflow dengan urutan sesuai step_order
   - Muncul di UI dengan config dari to_config()
   - Memiliki state fields dari output_fields


CARA MENGHAPUS AGENT:
---------------------

1. Hapus/comment import agent class
2. Hapus/comment dari AGENT_CLASSES list
3. (Opsional) Hapus file agent jika tidak dibutuhkan lagi


CARA MENGUBAH URUTAN WORKFLOW:
------------------------------

Ubah nilai step_order di masing-masing agent class.
Registry akan otomatis mengurutkan agent berdasarkan step_order.


ARSITEKTUR:
-----------

                    ┌─────────────────┐
                    │  Agent Classes  │
                    │  (BaseAgent)    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │    Registry     │
                    │  (this module)  │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
┌────────▼────────┐ ┌────────▼────────┐ ┌────────▼────────┐
│    Workflow     │ │      State      │ │       UI        │
│  (add_node)     │ │  (fields init)  │ │  (AGENTS_CONFIG)│
└─────────────────┘ └─────────────────┘ └─────────────────┘

"""

from typing import List, Type, Dict, Any, Callable
from .base import BaseAgent


# =============================================================================
# AGENT IMPORTS
# =============================================================================
# Import semua agent class di sini.
# Saat menambah agent baru, tambahkan import-nya di bagian ini.

from .orchestrator import OrchestratorAgent
from .product_spec import ProductSpecAgent
from .backend import BackendAgent
from .frontend import FrontendAgent
from .test import TestAgent
from .security import SecurityAgent
from .qa import QAAgent
from .devops import DevOpsAgent


# =============================================================================
# AGENT REGISTRATION
# =============================================================================
# Daftar semua agent class yang akan digunakan dalam workflow.
# Urutan di list ini TIDAK menentukan urutan eksekusi.
# Urutan eksekusi ditentukan oleh step_order di masing-masing agent.

AGENT_CLASSES: List[Type[BaseAgent]] = [
    OrchestratorAgent,      # Step 1: Orchestrator - mengatur workflow
    ProductSpecAgent,       # Step 2: Product Spec - spesifikasi teknis
    BackendAgent,           # Step 3: Backend - implementasi backend
    FrontendAgent,          # Step 4: Frontend - implementasi frontend
    TestAgent,              # Step 5: Testing - test suites
    SecurityAgent,          # Step 6: Security - threat modeling
    QAAgent,                # Step 7: QA Review - code review
    DevOpsAgent,            # Step 8: DevOps - Docker, CI/CD
]


# =============================================================================
# REGISTRY CLASS
# =============================================================================

class AgentRegistry:
    """
    Registry untuk mengelola semua agent.

    Registry ini:
    - Meng-instantiate semua agent class
    - Mengurutkan berdasarkan step_order
    - Menyediakan helper untuk workflow dan UI

    Usage:
        registry = AgentRegistry()

        # Dapatkan semua agent terurut
        for agent in registry.get_agents():
            print(agent.agent_name)

        # Dapatkan callable untuk workflow
        callables = registry.get_workflow_callables()

        # Dapatkan config untuk UI
        configs = registry.get_ui_configs()
    """

    def __init__(self, agent_classes: List[Type[BaseAgent]] = None):
        """
        Initialize registry dengan list agent classes.

        Args:
            agent_classes: List of agent classes. Default: AGENT_CLASSES
        """
        self._classes = agent_classes or AGENT_CLASSES
        self._agents: List[BaseAgent] = []
        self._by_id: Dict[str, BaseAgent] = {}
        self._initialize_agents()

    def _initialize_agents(self):
        """Instantiate semua agent dan urutkan berdasarkan step_order."""
        # Instantiate semua agent
        for cls in self._classes:
            agent = cls()
            self._agents.append(agent)
            self._by_id[agent.agent_id] = agent

        # Urutkan berdasarkan step_order
        self._agents.sort(key=lambda a: a.step_order)

    # =========================================================================
    # GETTERS
    # =========================================================================

    def get_agents(self) -> List[BaseAgent]:
        """
        Dapatkan semua agent instances, terurut berdasarkan step_order.

        Returns:
            List of BaseAgent instances
        """
        return self._agents

    def get_agent(self, agent_id: str) -> BaseAgent:
        """
        Dapatkan agent berdasarkan ID.

        Args:
            agent_id: ID agent

        Returns:
            BaseAgent instance

        Raises:
            KeyError: Jika agent_id tidak ditemukan
        """
        if agent_id not in self._by_id:
            raise KeyError(f"Agent '{agent_id}' tidak ditemukan di registry")
        return self._by_id[agent_id]

    def get_agent_ids(self) -> List[str]:
        """
        Dapatkan list agent IDs terurut.

        Returns:
            List of agent IDs
        """
        return [a.agent_id for a in self._agents]

    # =========================================================================
    # WORKFLOW HELPERS
    # =========================================================================

    def get_workflow_callables(self) -> Dict[str, Callable]:
        """
        Dapatkan dictionary agent_id -> callable untuk LangGraph.

        Gunakan ini saat membangun workflow:
            callables = registry.get_workflow_callables()
            for agent_id, callable in callables.items():
                workflow.add_node(agent_id, callable)

        Returns:
            Dict mapping agent_id ke callable agent
        """
        return {agent.agent_id: agent for agent in self._agents}

    def get_workflow_edges(self) -> List[tuple]:
        """
        Dapatkan list edge tuples untuk sequential workflow.

        Returns:
            List of (from_id, to_id) tuples
        """
        edges = []
        for i in range(len(self._agents) - 1):
            edges.append((self._agents[i].agent_id, self._agents[i + 1].agent_id))
        return edges

    def get_entry_point(self) -> str:
        """
        Dapatkan agent_id untuk entry point workflow.

        Returns:
            Agent ID dengan step_order terkecil
        """
        return self._agents[0].agent_id if self._agents else ""

    def get_exit_point(self) -> str:
        """
        Dapatkan agent_id untuk exit point workflow.

        Returns:
            Agent ID dengan step_order terbesar
        """
        return self._agents[-1].agent_id if self._agents else ""

    # =========================================================================
    # UI HELPERS
    # =========================================================================

    def get_ui_configs(self) -> List[Dict[str, Any]]:
        """
        Dapatkan list config untuk UI (AGENTS_CONFIG format).

        Returns:
            List of config dictionaries
        """
        return [agent.to_config() for agent in self._agents]

    # =========================================================================
    # STATE HELPERS
    # =========================================================================

    def get_output_fields(self) -> List[str]:
        """
        Dapatkan semua output field names dari semua agent.

        Berguna untuk membangun initial state.

        Returns:
            List of unique field names
        """
        fields = set()
        for agent in self._agents:
            for field_name, _, _ in agent.output_fields:
                fields.add(field_name)
        return list(fields)

    def get_field_file_map(self) -> List[tuple]:
        """
        Dapatkan mapping field_name -> filename untuk file persistence.

        Returns:
            List of (field_name, filename) tuples
        """
        mapping = []
        for agent in self._agents:
            for field_name, filename, _ in agent.output_fields:
                mapping.append((field_name, filename))
        return mapping

    # =========================================================================
    # DEBUG
    # =========================================================================

    def print_pipeline(self):
        """Print pipeline workflow untuk debugging."""
        print("\n=== SATGAS Pipeline ===\n")
        for i, agent in enumerate(self._agents):
            prefix = "└──" if i == len(self._agents) - 1 else "├──"
            print(f"{prefix} [{agent.step_order}] {agent.agent_name}")
            print(f"    │   ID: {agent.agent_id}")
            print(f"    │   Description: {agent.description}")
            if agent.output_fields:
                outputs = ", ".join(f[1] for f in agent.output_fields)
                print(f"    │   Outputs: {outputs}")
            print()


# =============================================================================
# GLOBAL REGISTRY INSTANCE
# =============================================================================
# Instance ini akan digunakan oleh workflow dan UI

registry = AgentRegistry()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================
# Fungsi-fungsi ini untuk kemudahan akses tanpa harus import registry

def get_agents() -> List[BaseAgent]:
    """Shortcut untuk registry.get_agents()."""
    return registry.get_agents()


def get_agent(agent_id: str) -> BaseAgent:
    """Shortcut untuk registry.get_agent()."""
    return registry.get_agent(agent_id)


def get_ui_configs() -> List[Dict[str, Any]]:
    """Shortcut untuk registry.get_ui_configs()."""
    return registry.get_ui_configs()


# =============================================================================
# LEGACY COMPATIBILITY
# =============================================================================
# Untuk backward compatibility dengan kode lama yang menggunakan function-based agents

def orchestrator_agent(state): return registry.get_agent("orchestrator").execute(state)
def product_spec_agent(state): return registry.get_agent("product_spec").execute(state)
def backend_engineer_agent(state): return registry.get_agent("backend").execute(state)
def frontend_engineer_agent(state): return registry.get_agent("frontend").execute(state)
def test_engineer_agent(state): return registry.get_agent("test").execute(state)
def security_agent(state): return registry.get_agent("security").execute(state)
def qa_critic_agent(state): return registry.get_agent("qa").execute(state)
def devops_agent(state): return registry.get_agent("devops").execute(state)
