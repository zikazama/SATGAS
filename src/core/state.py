"""State definition for the app generation workflow."""
from typing import TypedDict, Any

# Use typing_extensions for better compatibility with LangGraph's type processing
try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated


def merge_str(left: Any, right: Any) -> str:
    """Reducer that merges string values for parallel execution.

    When parallel branches converge, this determines how to merge values:
    - If right has a value, use it (last write wins)
    - Otherwise keep left value
    - Handles None and empty string cases
    """
    # Handle None cases
    if right is None:
        return left if left is not None else ""
    if left is None:
        return right if right else ""

    # Both have values - prefer non-empty right, then non-empty left
    if right:
        return right
    return left if left else ""


def merge_int(left: Any, right: Any) -> int:
    """Reducer for integer fields - keeps the maximum value."""
    left_val = left if isinstance(left, int) else 0
    right_val = right if isinstance(right, int) else 0
    return max(left_val, right_val)


class AppGenerationState(TypedDict, total=True):
    """State yang digunakan sepanjang workflow multi-agent.

    Fields use Annotated types with reducers to support parallel execution.
    When parallel branches (backend+frontend, test+security+qa) converge,
    the reducers determine how to merge values.
    """
    # Core fields - each agent writes to its own field
    prompt: Annotated[str, merge_str]
    spec: Annotated[str, merge_str]
    acceptance_tests: Annotated[str, merge_str]
    tasks: Annotated[str, merge_str]

    # Parallel Phase 2: Backend & Frontend run simultaneously
    backend_code: Annotated[str, merge_str]
    frontend_code: Annotated[str, merge_str]

    # Parallel Phase 3: Test, Security, QA run simultaneously
    test_plan: Annotated[str, merge_str]
    threat_model: Annotated[str, merge_str]
    security_requirements: Annotated[str, merge_str]
    security_findings: Annotated[str, merge_str]
    qa_findings: Annotated[str, merge_str]

    # Phase 4: DevOps (sequential)
    docker_compose: Annotated[str, merge_str]
    ci_config: Annotated[str, merge_str]
    runbook: Annotated[str, merge_str]

    # Status tracking
    status: Annotated[str, merge_str]
    iterations: Annotated[int, merge_int]


def create_initial_state(prompt: str) -> AppGenerationState:
    """Create initial state with the given prompt."""
    return {
        "prompt": prompt,
        "spec": "",
        "acceptance_tests": "",
        "backend_code": "",
        "frontend_code": "",
        "qa_findings": "",
        "test_plan": "",
        "threat_model": "",
        "security_requirements": "",
        "security_findings": "",
        "docker_compose": "",
        "ci_config": "",
        "runbook": "",
        "status": "started",
        "iterations": 0,
        "tasks": ""
    }
