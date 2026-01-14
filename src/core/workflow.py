"""
Workflow Module
===============

Modul ini mendefinisikan LangGraph workflow untuk SATGAS.
Workflow dibangun secara dinamis berdasarkan agent yang terdaftar di registry.

ARSITEKTUR:
-----------

    AgentRegistry
         |
         +-- get_agents()        -> List agent terurut
         +-- get_workflow_edges() -> Edge connections
         +-- get_entry_point()   -> First agent
         +-- get_exit_point()    -> Last agent
                |
                v
    StateGraph (LangGraph)
         |
         +-- add_node(id, agent) -> Register agent sebagai node
         +-- add_edge(a, b)      -> Connect nodes
         +-- set_entry_point()   -> Define start
         +-- compile()           -> Create executable app
                |
                v
    Compiled App
         |
         +-- invoke(state)       -> Run workflow


CARA KERJA:
-----------

1. Registry menyediakan list agent yang sudah terurut berdasarkan step_order
2. create_workflow() membuat StateGraph dengan nodes dari registry
3. Edges dibuat secara sequential: agent1 -> agent2 -> ... -> END
4. Workflow di-compile menjadi executable app


CUSTOMIZATION:
--------------

Untuk mengubah workflow:

1. Menambah/menghapus agent:
   - Edit registry.py (AGENT_CLASSES)
   - Workflow akan otomatis ter-update

2. Mengubah urutan:
   - Ubah step_order di masing-masing agent class
   - Registry akan mengurutkan ulang

3. Membuat branching/conditional workflow:
   - Override create_workflow() dengan custom logic
   - Gunakan conditional edges dari LangGraph

"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import AppGenerationState
from ..agents import registry


def create_workflow() -> StateGraph:
    """
    Buat dan konfigurasi LangGraph workflow.

    Workflow dibuat secara dinamis berdasarkan agent yang terdaftar
    di registry. Agent diurutkan berdasarkan step_order dan
    di-connect secara sequential.

    Returns:
        StateGraph: Workflow yang belum di-compile

    Raises:
        ValueError: Jika tidak ada agent yang terdaftar
    """
    # Dapatkan semua agent dari registry
    agents = registry.get_agents()

    if not agents:
        raise ValueError("Tidak ada agent yang terdaftar di registry")

    # Buat workflow
    workflow = StateGraph(AppGenerationState)

    # =========================================================================
    # ADD NODES
    # =========================================================================
    # Setiap agent menjadi satu node di workflow.
    # Agent callable karena mengimplementasikan __call__().

    for agent in agents:
        workflow.add_node(agent.agent_id, agent)

    # =========================================================================
    # ADD EDGES
    # =========================================================================
    # Edges dibuat secara sequential berdasarkan urutan dari registry.
    # Agent terakhir di-connect ke END.

    # Set entry point (agent pertama)
    entry_point = registry.get_entry_point()
    workflow.set_entry_point(entry_point)

    # Add sequential edges
    edges = registry.get_workflow_edges()
    for from_id, to_id in edges:
        workflow.add_edge(from_id, to_id)

    # Connect last agent to END
    exit_point = registry.get_exit_point()
    workflow.add_edge(exit_point, END)

    return workflow


def create_parallel_workflow() -> StateGraph:
    """
    Buat workflow dengan parallel execution untuk optimasi performa.

    Workflow Structure:
    ==================

        Phase 1 (Sequential):
            Orchestrator → Product Spec

        Phase 2 (Parallel):
            Backend + Frontend (keduanya hanya butuh spec)

        Phase 3 (Parallel):
            Testing + Security + QA (ketiganya butuh backend & frontend code)

        Phase 4 (Sequential):
            DevOps (final step)

    Visualisasi:
    ============

            ┌─────────────┐
            │ Orchestrator │
            └──────┬──────┘
                   │
            ┌──────▼──────┐
            │ Product Spec │
            └──────┬──────┘
                   │
           ┌───────┴───────┐
           │               │
      ┌────▼────┐    ┌────▼────┐
      │ Backend │    │ Frontend │  ← Parallel
      └────┬────┘    └────┬────┘
           │               │
           └───────┬───────┘
                   │
         ┌─────────┼─────────┐
         │         │         │
    ┌────▼───┐ ┌───▼───┐ ┌───▼──┐
    │Testing │ │Security│ │  QA  │  ← Parallel
    └────┬───┘ └───┬───┘ └───┬──┘
         │         │         │
         └─────────┼─────────┘
                   │
            ┌──────▼──────┐
            │   DevOps    │
            └─────────────┘

    Returns:
        StateGraph: Workflow dengan parallel execution
    """
    workflow = StateGraph(AppGenerationState)

    # =========================================================================
    # ADD NODES
    # =========================================================================
    agents = registry.get_agents()
    for agent in agents:
        workflow.add_node(agent.agent_id, agent)

    # =========================================================================
    # PHASE 1: Sequential (Orchestrator → Product Spec)
    # =========================================================================
    workflow.set_entry_point("orchestrator")
    workflow.add_edge("orchestrator", "product_spec")

    # =========================================================================
    # PHASE 2: Parallel (Backend + Frontend)
    # =========================================================================
    # Fan-out: product_spec → backend AND frontend
    workflow.add_edge("product_spec", "backend")
    workflow.add_edge("product_spec", "frontend")

    # =========================================================================
    # PHASE 3: Parallel (Testing + Security + QA)
    # =========================================================================
    # Fan-in then fan-out: backend & frontend → test, security, qa
    # LangGraph akan menunggu semua incoming edges selesai sebelum lanjut
    workflow.add_edge("backend", "test")
    workflow.add_edge("frontend", "test")

    workflow.add_edge("backend", "security")
    workflow.add_edge("frontend", "security")

    workflow.add_edge("backend", "qa")
    workflow.add_edge("frontend", "qa")

    # =========================================================================
    # PHASE 4: Sequential (DevOps)
    # =========================================================================
    # Fan-in: test, security, qa → devops
    workflow.add_edge("test", "devops")
    workflow.add_edge("security", "devops")
    workflow.add_edge("qa", "devops")

    # Final: devops → END
    workflow.add_edge("devops", END)

    return workflow


def create_workflow_with_custom_order(agent_order: list) -> StateGraph:
    """
    Buat workflow dengan urutan agent custom.

    Gunakan fungsi ini jika ingin urutan berbeda dari default
    tanpa mengubah step_order di agent class.

    Args:
        agent_order: List of agent_id dalam urutan yang diinginkan

    Returns:
        StateGraph: Workflow dengan urutan custom

    Example:
        workflow = create_workflow_with_custom_order([
            "orchestrator",
            "product_spec",
            "backend",
            "security",  # Security sebelum frontend
            "frontend",
            "test",
            "qa",
            "devops"
        ])
    """
    workflow = StateGraph(AppGenerationState)

    # Add nodes berdasarkan urutan
    for agent_id in agent_order:
        agent = registry.get_agent(agent_id)
        workflow.add_node(agent_id, agent)

    # Set entry point
    workflow.set_entry_point(agent_order[0])

    # Add sequential edges
    for i in range(len(agent_order) - 1):
        workflow.add_edge(agent_order[i], agent_order[i + 1])

    # Connect last to END
    workflow.add_edge(agent_order[-1], END)

    return workflow


# =============================================================================
# COMPILED WORKFLOW
# =============================================================================
# Instance global yang siap digunakan.
# Import ini dari module lain untuk menjalankan workflow.

# Checkpointer untuk parallel execution - diperlukan untuk state merging
# saat parallel branches (backend+frontend, test+security+qa) converge
memory = MemorySaver()

# Gunakan parallel workflow untuk performa optimal
# Ganti dengan create_workflow() jika ingin sequential execution
app = create_parallel_workflow().compile(checkpointer=memory)

# Alternative: sequential workflow (tidak perlu checkpointer)
# app = create_workflow().compile()


# =============================================================================
# DEBUG HELPER
# =============================================================================

def print_workflow():
    """Print workflow structure untuk debugging."""
    print("\n=== SATGAS Workflow (Sequential) ===\n")
    print(f"Entry point: {registry.get_entry_point()}")
    print(f"Exit point:  {registry.get_exit_point()}")
    print("\nNodes:")
    for agent in registry.get_agents():
        print(f"  - {agent.agent_id} ({agent.agent_name})")
    print("\nEdges:")
    for from_id, to_id in registry.get_workflow_edges():
        print(f"  {from_id} -> {to_id}")
    print(f"  {registry.get_exit_point()} -> END")
    print()


def print_parallel_workflow():
    """Print parallel workflow structure untuk debugging."""
    print("\n=== SATGAS Workflow (Parallel) ===\n")
    print("Phase 1 - Sequential:")
    print("  orchestrator -> product_spec")
    print("\nPhase 2 - Parallel:")
    print("  product_spec -> backend")
    print("  product_spec -> frontend")
    print("\nPhase 3 - Parallel (menunggu backend & frontend selesai):")
    print("  backend, frontend -> test")
    print("  backend, frontend -> security")
    print("  backend, frontend -> qa")
    print("\nPhase 4 - Sequential (menunggu test, security, qa selesai):")
    print("  test, security, qa -> devops")
    print("  devops -> END")
    print()
    print("Visualisasi:")
    print("""
            ┌─────────────┐
            │ Orchestrator │
            └──────┬──────┘
                   │
            ┌──────▼──────┐
            │ Product Spec │
            └──────┬──────┘
                   │
           ┌───────┴───────┐
           │               │
      ┌────▼────┐    ┌────▼────┐
      │ Backend │    │ Frontend │  ← Parallel
      └────┬────┘    └────┬────┘
           │               │
           └───────┬───────┘
                   │
         ┌─────────┼─────────┐
         │         │         │
    ┌────▼───┐ ┌───▼───┐ ┌───▼──┐
    │Testing │ │Security│ │  QA  │  ← Parallel
    └────┬───┘ └───┬───┘ └───┬──┘
         │         │         │
         └─────────┼─────────┘
                   │
            ┌──────▼──────┐
            │   DevOps    │
            └─────────────┘
    """)
