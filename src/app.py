"""SATGAS - Streamlit UI."""
import base64
import re
import sys
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Callable

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

from config.settings import SETTINGS
from src.core import AppGenerationState, app as graph_app, llm
from src.core.state import create_initial_state
from src.utils.helpers import sanitize_for_output, format_exception, slugify, StreamingFileSaver
from src.utils.formatters import format_project, check_formatters_available

# Thread-safe lock for UI updates during parallel execution
_ui_lock = threading.RLock()  # Use RLock to allow re-entrant locking


def _get_thread_safe_callback(callback: Callable) -> Callable:
    """
    Wrap a callback to be thread-safe for Streamlit.

    This captures the main thread's ScriptRunContext and applies it
    when the callback is executed from a worker thread (e.g., during
    parallel agent execution in LangGraph).
    """
    ctx = get_script_run_ctx()

    def wrapped(*args, **kwargs):
        # Add the captured context to the current thread
        if ctx is not None:
            try:
                add_script_run_ctx(threading.current_thread(), ctx)
            except Exception:
                pass  # Ignore context errors

        # Try to acquire lock with timeout to prevent blocking
        acquired = _ui_lock.acquire(blocking=True, timeout=1.0)
        if not acquired:
            # If lock not available, skip UI update but continue execution
            return None

        try:
            return callback(*args, **kwargs)
        except Exception:
            # If UI update fails, still continue execution
            pass
        finally:
            _ui_lock.release()

    return wrapped


# Logo path
LOGO_PATH = Path(__file__).parent.parent / "assets" / "satgas-logo.png"


def get_logo_base64() -> str:
    """Get logo as base64 string for HTML embedding."""
    if LOGO_PATH.exists():
        with open(LOGO_PATH, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""


# Agent name mapping from LLM to config
AGENT_NAME_MAP = {
    "Orchestrator": "orchestrator",
    "Product & Spec": "product_spec",
    "Backend Engineer": "backend",
    "Frontend Engineer": "frontend",
    "Test Engineer": "test",
    "Security": "security",
    "QA Critic": "qa",
    "DevOps": "devops",
}

# Page config with logo as favicon
st.set_page_config(
    page_title="SATGAS",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else "S",
    layout="wide"
)

# Custom CSS with Tactical Theme
st.markdown("""
<style>
/* ===========================================
   SATGAS COLOR PALETTE (Tactical Theme)
   ===========================================
   Primary 01 — Tactical Green: #4BA91C
   Primary 02 — Deep Tactical Green: #356D21
   Secondary 01 — Gunmetal: #30353A
   Secondary 02 — Charcoal: #252A2F
   Accent 01 — Neon Vision Green: #6BE31E
   Accent 02 — Lime Highlight: #A7E55B
   Neutral 01 — Off White: #E0E8E6
   Neutral 02 — Steel Gray: #9EA7A6
   Neutral 03 — Light Gray: #BCC1C3
   Stroke 01 — Dark Outline: #1C1F23
   BG Dark 01: #252A2F
   BG Dark 02: #1C1F23
   =========================================== */

/* Main container */
.main .block-container {
    padding-top: 2rem;
    max-width: 1200px;
}

/* Header styling */
.app-header {
    background: linear-gradient(135deg, #1C1F23 0%, #252A2F 50%, #30353A 100%);
    padding: 1.5rem 2rem;
    border-radius: 8px;
    margin-bottom: 1.5rem;
    color: #E0E8E6;
    display: flex;
    align-items: center;
    gap: 1.5rem;
    border: 1px solid #30353A;
    box-shadow: 0 4px 20px rgba(28, 31, 35, 0.5);
}
.app-header .logo {
    width: 64px;
    height: 64px;
    border-radius: 12px;
    object-fit: contain;
    background: rgba(75, 169, 28, 0.15);
    padding: 8px;
    border: 1px solid #4BA91C;
}
.app-header .header-text h1 {
    margin: 0;
    font-size: 1.8rem;
    font-weight: 600;
    letter-spacing: 0.5px;
    color: #6BE31E;
    text-shadow: 0 0 10px rgba(107, 227, 30, 0.3);
}
.app-header .header-text p {
    margin: 0.5rem 0 0 0;
    color: #9EA7A6;
    font-size: 0.9rem;
}

/* Agent step badges */
.step-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: #30353A;
    color: #9EA7A6;
    font-size: 0.75rem;
    font-weight: 600;
    margin-right: 8px;
    border: 1px solid #30353A;
}
.step-badge.active {
    background: #6BE31E;
    color: #1C1F23;
    border-color: #6BE31E;
    box-shadow: 0 0 8px rgba(107, 227, 30, 0.5);
}
.step-badge.completed {
    background: #4BA91C;
    color: #1C1F23;
    border-color: #356D21;
}

/* Pipeline visualization */
.pipeline-container {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem 0;
    overflow-x: auto;
}
.pipeline-step {
    display: flex;
    flex-direction: column;
    align-items: center;
    min-width: 80px;
    position: relative;
}
.pipeline-step .step-num {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
    font-size: 0.85rem;
    margin-bottom: 6px;
    transition: all 0.3s ease;
    border: 2px solid #30353A;
}
.pipeline-step .step-name {
    font-size: 0.7rem;
    text-align: center;
    color: #9EA7A6;
    max-width: 70px;
}
.pipeline-connector {
    flex: 1;
    height: 2px;
    background: linear-gradient(90deg, #356D21, #4BA91C);
    margin: 0 4px;
    margin-bottom: 20px;
}

/* Status cards */
.status-card {
    padding: 8px 12px;
    margin: 4px 0;
    border-radius: 6px;
    font-size: 0.85rem;
    display: flex;
    align-items: center;
    gap: 8px;
    border: 1px solid #30353A;
}
.status-card.running {
    background: linear-gradient(135deg, #4BA91C 0%, #6BE31E 100%);
    border-left: 3px solid #A7E55B;
    color: #1C1F23;
    font-weight: 500;
}
.status-card.running b {
    color: #1C1F23;
}
.status-card.completed {
    background: linear-gradient(135deg, #252A2F 0%, #30353A 100%);
    border-left: 3px solid #4BA91C;
    color: #A7E55B;
}
.status-card.pending {
    background: #252A2F;
    color: #9EA7A6;
}

/* File list */
.file-item {
    padding: 4px 8px;
    font-size: 0.8rem;
    font-family: monospace;
    color: #1A1D21;
    background: rgba(75, 169, 28, 0.25);
    border-radius: 4px;
    margin: 2px 0;
    border-left: 2px solid #4BA91C;
}
.files-more {
    color: #3A4A48;
    font-size: 0.75rem;
    padding: 4px 8px;
}
.files-total {
    margin-top: 8px;
    font-weight: 600;
    font-size: 0.85rem;
    color: #2D7A10;
}
.files-empty {
    color: #3A4A48;
    font-size: 0.85rem;
}

/* Expander styling */
.stExpander {
    border: 1px solid #30353A !important;
    border-radius: 8px !important;
    margin-bottom: 8px;
    background: #252A2F !important;
}
.stExpander > details {
    background: #252A2F !important;
}
.stExpander > details > summary {
    color: #E0E8E6 !important;
    background: #30353A !important;
    padding: 0.75rem 1rem !important;
    border-radius: 8px !important;
}
.stExpander > details > summary:hover {
    background: #3A4045 !important;
    color: #6BE31E !important;
}
.stExpander > details > summary > span {
    color: #E0E8E6 !important;
}
.stExpander > details > summary > span p {
    color: #E0E8E6 !important;
    font-weight: 500;
}
.stExpander > details[open] > summary {
    background: linear-gradient(135deg, #356D21 0%, #4BA91C 100%) !important;
    color: #1C1F23 !important;
    border-bottom-left-radius: 0 !important;
    border-bottom-right-radius: 0 !important;
}
.stExpander > details[open] > summary > span,
.stExpander > details[open] > summary > span p {
    color: #1C1F23 !important;
}
/* Expander arrow icon */
.stExpander > details > summary svg {
    color: #9EA7A6 !important;
}
.stExpander > details[open] > summary svg {
    color: #1C1F23 !important;
}

/* Metrics */
.metric-card {
    background: linear-gradient(135deg, #252A2F 0%, #30353A 100%);
    padding: 1rem;
    border-radius: 8px;
    text-align: center;
    border: 1px solid #30353A;
}
.metric-value {
    font-size: 1.5rem;
    font-weight: 600;
    color: #6BE31E;
}
.metric-label {
    font-size: 0.8rem;
    color: #9EA7A6;
}

/* Footer */
.app-footer {
    text-align: center;
    padding: 1rem;
    color: #9EA7A6;
    font-size: 0.8rem;
    border-top: 1px solid #30353A;
    margin-top: 2rem;
}
.app-footer a {
    color: #9EA7A6 !important;
    text-decoration: underline;
}
.app-footer a:hover {
    color: #BCC1C3 !important;
}

/* How to use box */
.how-to-box {
    background: linear-gradient(135deg, #252A2F 0%, #30353A 100%);
    border: 1px solid #30353A;
    border-radius: 8px;
    padding: 1rem 1.5rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 2px 10px rgba(28, 31, 35, 0.3);
}
.how-to-box h4 {
    margin: 0 0 0.75rem 0;
    color: #6BE31E;
    font-size: 1rem;
}
.how-to-box ol {
    margin: 0;
    padding-left: 1.25rem;
    color: #E0E8E6;
}
.how-to-box li {
    margin-bottom: 0.5rem;
    font-size: 0.9rem;
    color: #BCC1C3;
}
.how-to-box code {
    background: #1C1F23;
    color: #A7E55B;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.85rem;
    border: 1px solid #30353A;
}

/* Output location box */
.output-box {
    background: linear-gradient(135deg, #4BA91C 0%, #6BE31E 100%);
    border: 1px solid #A7E55B;
    border-radius: 8px;
    padding: 1rem 1.5rem;
    margin: 1rem 0;
    box-shadow: 0 4px 15px rgba(75, 169, 28, 0.3);
}
.output-box h4 {
    margin: 0 0 0.5rem 0;
    color: #1C1F23;
    font-size: 1rem;
    font-weight: 600;
}
.output-box .path {
    background: #1C1F23;
    color: #6BE31E;
    padding: 8px 12px;
    border-radius: 4px;
    font-family: monospace;
    font-size: 0.85rem;
    word-break: break-all;
    border: 1px solid #30353A;
}
.output-box .hint {
    margin-top: 0.75rem;
    font-size: 0.85rem;
    color: #1C1F23;
}
</style>
""", unsafe_allow_html=True)

# Projects directory setup
_PROJECTS_INIT_ERROR: OSError | None = None
_PROJECTS_INIT_DONE: bool = False


def _setup_projects_dir() -> None:
    global _PROJECTS_INIT_ERROR, _PROJECTS_INIT_DONE
    if _PROJECTS_INIT_DONE:
        return
    try:
        SETTINGS.PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
        test_path = SETTINGS.PROJECTS_DIR / ".permcheck"
        test_path.write_text("ok", encoding="utf-8")
        test_path.unlink()
        _PROJECTS_INIT_ERROR = None
        _PROJECTS_INIT_DONE = True
    except OSError as exc:
        _PROJECTS_INIT_ERROR = exc
        _PROJECTS_INIT_DONE = True


_setup_projects_dir()


def _persist_project_artifacts(prompt: str, result: AppGenerationState, project_name: str = "") -> tuple[str, list[str]]:
    """Save generated artifacts to disk."""
    _setup_projects_dir()
    if _PROJECTS_INIT_ERROR is not None:
        raise OSError(f"Folder `{SETTINGS.PROJECTS_DIR}` tidak bisa ditulis: {_PROJECTS_INIT_ERROR}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Use project_name if provided, otherwise fallback to prompt slug
    if project_name and project_name.strip():
        slug = slugify(project_name.strip())
    else:
        slug = slugify(prompt[:50])
    folder = SETTINGS.PROJECTS_DIR / f"{timestamp}_{slug}"
    folder.mkdir(parents=True, exist_ok=True)

    saved_files: list[str] = []
    for key, filename in SETTINGS.FIELD_FILE_MAP:
        if key == "prompt":
            value = prompt
        else:
            value = result.get(key, "")
        if not value or not value.strip():
            continue

        target_path = folder / filename
        target_path.write_text(value, encoding="utf-8")
        saved_files.append(filename)

    return str(folder), saved_files


def render_agent_card(agent: dict, result: dict, expanded: bool = False):
    """Render a single agent's output as an expandable card."""
    step = agent["step"]
    name = agent["name"]
    desc = agent["description"]

    # Check if agent has output
    has_output = any(result.get(out[0], "").strip() for out in agent["outputs"])
    status = "[Done]" if has_output else "[Pending]"

    with st.expander(f"Step {step}: {name} - {desc} {status}", expanded=expanded):
        if not has_output:
            st.info("Belum ada output dari agent ini.")
            return

        for output_key, filename, lang in agent["outputs"]:
            content = result.get(output_key, "")
            if content and content.strip():
                st.markdown(f"**{filename}**")
                if lang == "python":
                    st.code(content, language="python")
                elif lang == "javascript":
                    st.code(content, language="javascript")
                elif lang == "yaml":
                    st.code(content, language="yaml")
                elif lang == "json":
                    st.code(content, language="json")
                elif lang == "markdown":
                    with st.container():
                        st.markdown(content)
                else:
                    st.text(content)
                st.divider()


def render_workflow_diagram():
    """Render the workflow diagram showing agent connections."""
    st.markdown("### Pipeline Overview")

    # Colors that need dark text for readability (light backgrounds)
    light_colors = {"#6BE31E", "#A7E55B", "#4BA91C"}

    # Create pipeline visualization
    pipeline_html = '<div class="pipeline-container">'
    for idx, agent in enumerate(SETTINGS.AGENTS_CONFIG):
        color = agent["color"]
        # Use dark text for light backgrounds, white for dark backgrounds
        text_color = "#1C1F23" if color.upper() in light_colors else "#E0E8E6"
        pipeline_html += f'''
        <div class="pipeline-step">
            <div class="step-num" style="background:{color};color:{text_color};">{agent["step"]}</div>
            <div class="step-name">{agent["name"]}</div>
        </div>
        '''
        if idx < len(SETTINGS.AGENTS_CONFIG) - 1:
            pipeline_html += '<div class="pipeline-connector"></div>'
    pipeline_html += '</div>'

    st.markdown(pipeline_html, unsafe_allow_html=True)


# Header with logo
logo_base64 = get_logo_base64()
if logo_base64:
    header_html = f"""
    <div class="app-header">
        <img src="data:image/png;base64,{logo_base64}" alt="SATGAS Logo" class="logo">
        <div class="header-text">
            <h1>SATGAS</h1>
            <p>Scalable Agent-to-agent Task Generation & Automation Service</p>
        </div>
    </div>
    """
else:
    header_html = """
    <div class="app-header">
        <div class="header-text">
            <h1>SATGAS</h1>
            <p>Scalable Agent-to-agent Task Generation & Automation Service</p>
        </div>
    </div>
    """
st.markdown(header_html, unsafe_allow_html=True)

# How to Use section
st.markdown(f"""
<div class="how-to-box">
    <h4>Cara Menggunakan</h4>
    <ol>
        <li>Masukkan <strong>nama project</strong> (opsional) - akan menjadi nama folder output</li>
        <li>Tuliskan deskripsi aplikasi yang ingin Anda buat di kolom input di bawah</li>
        <li>Sebutkan tech stack yang diinginkan (contoh: <code>React</code>, <code>FastAPI</code>, <code>PostgreSQL</code>)</li>
        <li>Klik tombol <strong>Generate</strong> untuk memulai proses</li>
        <li>Tunggu hingga semua agent selesai memproses</li>
        <li>Aplikasi yang di-generate akan tersimpan di folder: <code>{SETTINGS.PROJECTS_DIR}/YYYYMMDD_HHMMSS_nama-project</code></li>
    </ol>
</div>
""", unsafe_allow_html=True)

# Initialize session state for active agent tracking
if "active_agent" not in st.session_state:
    st.session_state.active_agent = None
if "saved_files" not in st.session_state:
    st.session_state.saved_files = []
if "project_folder" not in st.session_state:
    st.session_state.project_folder = None
if "project_name" not in st.session_state:
    st.session_state.project_name = ""

# Per-agent output tracking (must be defined before _update_sidebar_status)
agent_logs: Dict[str, List[str]] = {agent["id"]: [] for agent in SETTINGS.AGENTS_CONFIG}
agent_containers: Dict[str, st.delta_generator.DeltaGenerator] = {}
current_agent_id: str = "orchestrator"
file_saver: StreamingFileSaver | None = None

# Sidebar for settings
with st.sidebar:
    st.markdown("### Settings")
    show_workflow = st.checkbox("Show pipeline diagram", value=True)
    auto_expand = st.checkbox("Auto-expand all agents", value=False)
    st.divider()

    st.markdown("### Agent Status")
    sidebar_status = st.empty()
    st.divider()

    st.markdown("### Generated Files")
    files_status = st.empty()


def _update_sidebar_status():
    """Update sidebar with current agent status."""
    status_html = ""
    for agent in SETTINGS.AGENTS_CONFIG:
        agent_id = agent["id"]
        step = agent["step"]
        name = agent["name"]

        if agent_id == st.session_state.active_agent:
            # Currently running
            status_html += f'<div class="status-card running"><span class="step-badge active">{step}</span><b>{name}</b> - Running...</div>'
        elif agent_logs.get(agent_id) and len(agent_logs[agent_id]) > 1:
            # Completed
            status_html += f'<div class="status-card completed"><span class="step-badge completed">{step}</span>{name} - Done</div>'
        else:
            # Pending
            status_html += f'<div class="status-card pending"><span class="step-badge">{step}</span>{name}</div>'

    sidebar_status.markdown(status_html, unsafe_allow_html=True)


def _update_files_status():
    """Update sidebar with saved files list."""
    if not st.session_state.saved_files:
        files_status.markdown('<div class="files-empty">No files yet...</div>', unsafe_allow_html=True)
        return

    files_html = ""
    for filepath in st.session_state.saved_files[-10:]:  # Show last 10 files
        files_html += f'<div class="file-item">{filepath}</div>'

    total = len(st.session_state.saved_files)
    if total > 10:
        files_html += f'<div class="files-more">...and {total - 10} more files</div>'

    files_html += f'<div class="files-total">Total: {total} files</div>'
    files_status.markdown(files_html, unsafe_allow_html=True)


_update_sidebar_status()
_update_files_status()

# Main content
st.markdown("### Project Details")

# Project name input
project_name = st.text_input(
    "Project Name",
    placeholder="my-awesome-app",
    help="Nama project untuk folder output. Akan menjadi: YYYYMMDD_HHMMSS_nama-project"
)

st.markdown("### Describe Your Application")
prompt = st.text_area(
    "Enter a detailed description of the application you want to generate:",
    height=120,
    placeholder=SETTINGS.PLACEHOLDER_EXAMPLE,
    label_visibility="collapsed"
)

col1, col2 = st.columns([1, 4])
with col1:
    generate_btn = st.button("Generate", type="primary", use_container_width=True)

status_placeholder = st.empty()


def _get_agent_id_from_line(line: str) -> str | None:
    """Extract agent ID from log line like '[Orchestrator] ...'"""
    match = re.match(r'\[([^\]]+)\]', line)
    if match:
        agent_name = match.group(1)
        return AGENT_NAME_MAP.get(agent_name)
    return None


def _on_file_saved(filepath: str, size: int) -> None:
    """Callback when a file is saved by StreamingFileSaver."""
    st.session_state.saved_files.append(filepath)
    _update_files_status()


def _stream_output(line: str) -> None:
    global current_agent_id, file_saver
    safe_line = sanitize_for_output(line)

    # Detect agent from line prefix (e.g., "[Backend Engineer] ...")
    detected_id = _get_agent_id_from_line(safe_line)
    detected_agent_name = None
    if detected_id:
        current_agent_id = detected_id
        st.session_state.active_agent = detected_id
        _update_sidebar_status()
        # Extract full agent name from line for file saver
        match = re.match(r'\[([^\]]+)\]', safe_line)
        if match:
            detected_agent_name = match.group(1)

    # Process line for incremental file saving
    # Pass agent name to file saver for parallel execution safety
    if file_saver is not None:
        # Remove agent prefix like "[Agent Name] " from the line
        line_for_saver = re.sub(r'^\[[^\]]+\]\s*', '', line)
        # Pass agent name so file saver can handle agent switches properly
        file_saver.process_line(line_for_saver, agent_name=detected_agent_name or current_agent_id)

    # Add line to current agent's log
    if current_agent_id in agent_logs:
        agent_logs[current_agent_id].append(safe_line)

        # Update the agent's container
        if current_agent_id in agent_containers:
            window = "\n".join(agent_logs[current_agent_id][-30:])
            agent_containers[current_agent_id].code(window, language="text")


if generate_btn:
    if prompt:
        # Reset logs and state
        for agent_id in agent_logs:
            agent_logs[agent_id] = []
        st.session_state.active_agent = "orchestrator"
        st.session_state.saved_files = []
        _update_sidebar_status()
        _update_files_status()

        # Create project folder upfront for incremental saving
        _setup_projects_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Use project_name if provided, otherwise fallback to prompt slug
        if project_name and project_name.strip():
            slug = slugify(project_name.strip())
        else:
            slug = slugify(prompt[:50])
        project_folder = SETTINGS.PROJECTS_DIR / f"{timestamp}_{slug}"
        project_folder.mkdir(parents=True, exist_ok=True)
        st.session_state.project_folder = str(project_folder)

        # Initialize streaming file saver with thread-safe callback
        file_saver = StreamingFileSaver(
            project_folder,
            on_file_saved=_get_thread_safe_callback(_on_file_saved)
        )

        # Save prompt file immediately
        (project_folder / "prompt.txt").write_text(prompt, encoding="utf-8")
        st.session_state.saved_files.append("prompt.txt")
        _update_files_status()

        # Use thread-safe callback for parallel execution
        llm.set_status_callback(_get_thread_safe_callback(_stream_output))
        initial_state = create_initial_state(prompt)

        status_placeholder.info(f"Running pipeline... Output directory: `{project_folder}`")

        # Create live output containers for each agent
        st.markdown("### Live Agent Output")
        st.caption("Click on an agent to view streaming output. Files are saved automatically as they are generated.")
        for agent in SETTINGS.AGENTS_CONFIG:
            with st.expander(f"Step {agent['step']}: {agent['name']} - {agent['description']}", expanded=False):
                agent_containers[agent["id"]] = st.empty()
                agent_containers[agent["id"]].code("Waiting...", language="text")

        result = None

        try:
            # Config dengan thread_id untuk checkpointer (diperlukan untuk parallel execution)
            config = {"configurable": {"thread_id": str(uuid.uuid4())}}
            result = graph_app.invoke(initial_state, config=config)
        except Exception as exc:
            status_placeholder.error(f"Generation failed: {format_exception(exc)}")
            st.error("Process failed. Check the agent output above for details.")
        else:
            status_placeholder.success("Generation completed successfully!")
        finally:
            llm.set_status_callback(None)
            st.session_state.active_agent = None
            _update_sidebar_status()
            # Finalize file saver to save any incomplete files
            if file_saver:
                file_saver.finalize()
                _update_files_status()

        if result:
            saved_files = st.session_state.saved_files
            if saved_files:
                # Run code formatters to fix indentation and styling
                format_placeholder = st.empty()
                format_placeholder.info("Formatting code with black & prettier...")

                formatters = check_formatters_available()
                if formatters.get("black") or formatters.get("prettier"):
                    format_stats = format_project(project_folder)
                    format_msg = f"Formatted {format_stats['formatted']} files"
                    if format_stats['failed'] > 0:
                        format_msg += f" ({format_stats['failed']} failed)"
                    format_placeholder.success(format_msg)
                else:
                    format_placeholder.warning(
                        "Formatters not found. Install `black` (pip install black) and/or "
                        "`prettier` (npm install -g prettier) for auto-formatting."
                    )

                # Show output location box
                st.markdown(f"""
                <div class="output-box">
                    <h4>Aplikasi Berhasil Di-generate!</h4>
                    <div class="path">{project_folder}</div>
                    <div class="hint">
                        Total {len(saved_files)} file telah dibuat. Buka folder di atas untuk melihat hasil generate.
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning("Folder created but no files were saved.")

            st.divider()

            # Show workflow diagram
            if show_workflow:
                render_workflow_diagram()

            st.markdown("### Agent Outputs")
            st.markdown("Click to expand/collapse each agent's output:")

            # Render each agent's output as a card
            for agent in SETTINGS.AGENTS_CONFIG:
                render_agent_card(agent, result, expanded=auto_expand)

            # Summary section
            st.divider()
            st.markdown("### Summary")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Agents", "8")
            with col2:
                completed = sum(
                    1 for a in SETTINGS.AGENTS_CONFIG
                    if any(result.get(o[0], "").strip() for o in a["outputs"])
                )
                st.metric("Completed", f"{completed}/8")
            with col3:
                total_files = len(saved_files)
                st.metric("Files Generated", total_files)

            st.markdown(f"**Final Status:** `{result.get('status', 'unknown')}`")

    else:
        st.error("Please enter an application description first.")

# Footer
st.markdown("""
<div class="app-footer">
    <strong>SATGAS</strong> - Scalable Agent-to-agent Task Generation & Automation Service<br>
    Powered by <strong>LangGraph</strong> + <strong>Multi-Provider LLM</strong><br>
    <span style="margin-top:8px;display:inline-block;">
        Created with all emotion by <a href="https://www.linkedin.com/in/fauzi-fadhlurrohman" target="_blank">Fauzi Fadhlurrohman</a>
    </span>
</div>
""", unsafe_allow_html=True)
