"""Helper utility functions."""
import locale
import re
import threading
from pathlib import Path
from typing import Callable

PREFERRED_ENCODING = locale.getpreferredencoding(False) or "utf-8"

# File markers for streaming output
FILE_START_MARKER = "===FILE:"
FILE_END_MARKER = "===END_FILE==="

# LLM commentary patterns to filter out (case-insensitive)
LLM_COMMENTARY_PATTERNS = [
    # English patterns
    r"^(?:I'll|I will|Let me|Let's|Here's|Here is|Now|First|Next|Finally|Starting)",
    r"^(?:Now I|I'm going|I am going|This will|We'll|We will)",
    r"^(?:Great|Perfect|Done|Completed|Finished|Created|Generated)",
    r"^(?:The following|Below is|Above is|Here are)",
    # Indonesian patterns
    r"^(?:Saya akan|Mari kita|Berikut|Sekarang|Pertama|Selanjutnya|Akhirnya)",
    r"^(?:Baik|Selesai|Dibuat|Dihasilkan|Terakhir)",
    r"^(?:Di bawah ini|Di atas adalah|Berikut adalah)",
    # Common LLM phrases
    r"^(?:\d+\.\s+)?(?:Create|Creating|Generate|Generating|Implement|Implementing)",
    r"^(?:\d+\.\s+)?(?:Buat|Membuat|Hasilkan|Menghasilkan|Implementasi)",
]


def is_llm_commentary(line: str) -> bool:
    """Check if a line looks like LLM commentary that should be filtered out.

    Only filters lines that are clearly commentary text, not code.
    Lines containing code-like content (parentheses, brackets, equals, etc.) are kept.
    """
    stripped = line.strip()

    # Empty lines are not commentary
    if not stripped:
        return False

    # Lines starting with file markers are not commentary
    if stripped.startswith(FILE_START_MARKER) or stripped == FILE_END_MARKER:
        return False

    # Lines that look like code (have programming syntax) are not commentary
    code_indicators = ['(', ')', '{', '}', '[', ']', '=', ';', ':', 'def ', 'class ',
                       'import ', 'from ', 'return ', 'if ', 'for ', 'while ', 'const ',
                       'let ', 'var ', 'function ', '=>', '->', '...', '===', '`']
    if any(indicator in stripped for indicator in code_indicators):
        return False

    # Check against commentary patterns
    for pattern in LLM_COMMENTARY_PATTERNS:
        if re.match(pattern, stripped, re.IGNORECASE):
            return True

    return False


def sanitize_for_output(text: str) -> str:
    """Sanitize text for safe output encoding."""
    try:
        text.encode(PREFERRED_ENCODING)
        return text
    except UnicodeEncodeError:
        return text.encode(PREFERRED_ENCODING, "replace").decode(PREFERRED_ENCODING)


def format_exception(exc: Exception) -> str:
    """Format exception message safely."""
    return sanitize_for_output(str(exc))


def slugify(text: str) -> str:
    """Convert text to URL-safe slug."""
    candidate = re.sub(r"[^a-z0-9]+", "-", text.lower())
    candidate = candidate.strip("-")
    return candidate or "project"


class AgentFileState:
    """Per-agent state for parallel execution safety.

    Each agent maintains its own file-building state so parallel agents
    don't interfere with each other's file content.
    """

    def __init__(self):
        self.current_file: str | None = None
        self.file_content: list[str] = []
        self.in_code_block: bool = False
        self.in_raw_mode: bool = False
        self.pending_file: str | None = None


class StreamingFileSaver:
    """Parse streaming output and save files incrementally.

    Supports multiple formats:
    1. ===FILE: path/to/file.py===
    2. ```language path/to/file.py (markdown code block)
    3. **File: path/to/file.py** or **path/to/file.py**

    For parallel execution, maintains per-agent state to prevent
    file content from getting mixed up when multiple agents output
    simultaneously.
    """

    # Regex patterns for detecting file paths - supports many tech stacks
    # Matches files from: Node.js, Python, PHP, Go, Ruby, Java, and more
    FILE_PATH_PATTERN = re.compile(
        r'^(?:'
        # Common folders with any file extension
        r'(?:backend|frontend|docs|src|app|tests?|config|\.github|public|lib|utils|services|'
        r'components|pages|hooks|models|schemas|routers|controllers|middleware|views|'
        r'resources|database|migrations|seeders|factories|routes|handlers|pkg|cmd|internal|'
        r'spec|features|helpers|assets|styles|scripts|templates|layouts|partials|'
        r'Http|Console|Providers|Exceptions|Events|Listeners|Jobs|Mail|Notifications|'
        r'main|java|kotlin|scala|test|integration|unit|e2e|cypress|playwright)/'
        r'[\w\-./]+\.\w+'
        r'|'
        # Root files with common extensions
        r'[\w\-]+\.(?:py|js|jsx|ts|tsx|json|yaml|yml|md|txt|css|scss|sass|less|html|htm|'
        r'php|go|rb|java|kt|scala|rs|c|cpp|h|hpp|cs|swift|m|vue|svelte|astro|'
        r'sql|graphql|gql|proto|xml|toml|ini|cfg|conf|lock|sum|mod|gradle|'
        r'blade\.php|erb|ejs|hbs|pug|twig|jinja|jinja2|mustache|'
        r'spec\.js|spec\.ts|test\.js|test\.ts|spec\.rb|_test\.go)'
        r'|'
        # Special files without extension or specific names
        r'(?:Dockerfile|docker-compose\.ya?ml|\.gitignore|\.env\.example|\.env|'
        r'README\.md|requirements\.txt|package\.json|package-lock\.json|yarn\.lock|'
        r'composer\.json|composer\.lock|Gemfile|Gemfile\.lock|go\.mod|go\.sum|'
        r'pom\.xml|build\.gradle|settings\.gradle|Cargo\.toml|Cargo\.lock|'
        r'Makefile|Rakefile|Procfile|\.dockerignore|\.editorconfig|\.prettierrc|'
        r'tsconfig\.json|jsconfig\.json|\.eslintrc\.json|\.babelrc|vite\.config\.\w+|'
        r'next\.config\.\w+|nuxt\.config\.\w+|tailwind\.config\.\w+|webpack\.config\.\w+|'
        r'artisan|manage\.py|setup\.py|pyproject\.toml)'
        r')$',
        re.IGNORECASE
    )

    def __init__(
        self,
        output_dir: Path,
        on_file_saved: Callable[[str, int], None] | None = None
    ):
        self.output_dir = output_dir
        self.on_file_saved = on_file_saved
        self.buffer: list[str] = []
        self.saved_files: list[str] = []
        self._lock = threading.Lock()  # Thread-safe access for parallel agents

        # Per-agent state for parallel execution
        # Key: agent_name (or "_default" for no agent specified)
        self._agent_states: dict[str, AgentFileState] = {}

    def _get_agent_state(self, agent_name: str | None) -> AgentFileState:
        """Get or create state for an agent.

        Each agent has its own file-building state to prevent mixing
        during parallel execution.
        """
        key = agent_name or "_default"
        if key not in self._agent_states:
            self._agent_states[key] = AgentFileState()
        return self._agent_states[key]

    def _extract_filepath(self, line: str) -> str | None:
        """Try to extract a file path from various formats."""
        stripped = line.strip()

        # Format 1: ===FILE: path/to/file.py===
        if stripped.startswith(FILE_START_MARKER) and stripped.endswith("==="):
            return stripped[len(FILE_START_MARKER):-3].strip()

        # Format 2: ```language path/to/file.py or ```language # path/to/file.py
        if stripped.startswith("```"):
            # Remove ``` and language identifier
            rest = stripped[3:].strip()
            # Remove language like 'python', 'javascript', etc
            parts = rest.split(None, 1)
            if len(parts) >= 1:
                # Check if first part is a language, second is path
                if len(parts) == 2:
                    potential_path = parts[1].lstrip('#').strip()
                    if self.FILE_PATH_PATTERN.match(potential_path):
                        return potential_path
                # Or path might be the whole thing after language
                potential_path = parts[0].lstrip('#').strip()
                if self.FILE_PATH_PATTERN.match(potential_path):
                    return potential_path
            return None

        # Format 3: **File: path** or **path** or **1. path**
        if "**" in stripped:
            # Extract content between ** markers
            match = re.search(r'\*\*([^*]+)\*\*', stripped)
            if match:
                inner = match.group(1).strip()
                # Remove numbering like "1. " or "1) "
                inner = re.sub(r'^[\d]+[.)]\s*', '', inner)
                # Remove common prefixes
                for prefix in ["File:", "file:", "Path:", "path:"]:
                    if inner.lower().startswith(prefix.lower()):
                        inner = inner[len(prefix):].strip()
                        break
                if self.FILE_PATH_PATTERN.match(inner):
                    return inner

        # Format 4: # path/to/file.py or ## path/to/file.py (markdown headers)
        if stripped.startswith("#"):
            inner = stripped.lstrip("#").strip()
            # Remove numbering like "1. " or "1) "
            inner = re.sub(r'^[\d]+[.)]\s*', '', inner)
            # Remove common prefixes
            for prefix in ["File:", "file:", "Path:", "path:"]:
                if inner.lower().startswith(prefix.lower()):
                    inner = inner[len(prefix):].strip()
                    break
            if self.FILE_PATH_PATTERN.match(inner):
                return inner

        # Format 5: Numbered list with file path: "1. backend/app/main.py" or "- backend/app/main.py"
        list_match = re.match(r'^(?:[\d]+[.)]\s*|-\s*|\*\s*)(.+)$', stripped)
        if list_match:
            potential = list_match.group(1).strip()
            # Remove trailing descriptions like " - description"
            potential = re.split(r'\s*[-–—]\s+', potential)[0].strip()
            if self.FILE_PATH_PATTERN.match(potential):
                return potential

        return None

    def _is_code_block_end(self, line: str) -> bool:
        """Check if line ends a code block."""
        return line.strip() == "```"

    def _is_file_end_marker(self, line: str) -> bool:
        """Check if line is a file end marker."""
        stripped = line.strip()
        return stripped == FILE_END_MARKER

    def process_line(self, line: str, agent_name: str | None = None) -> None:
        """Process a single line of streaming output.

        Args:
            line: The line to process
            agent_name: Optional agent name. Each agent maintains its own
                        file-building state for parallel execution safety.
        """
        with self._lock:
            # Get or create state for this agent
            state = self._get_agent_state(agent_name)

            # Strip agent prefix like "[Backend Engineer] "
            cleaned_line = re.sub(r'^\[[^\]]+\]\s*', '', line)
            stripped = cleaned_line.strip()

            # Filter out LLM commentary when NOT inside a file block
            # This prevents "I'll create...", "Saya akan..." etc. from polluting output
            if not state.in_raw_mode and not (state.in_code_block and state.current_file):
                if is_llm_commentary(cleaned_line):
                    # Skip this line - it's LLM commentary, not code
                    return

            # Check for explicit end marker (===END_FILE===)
            if self._is_file_end_marker(cleaned_line) and state.current_file:
                self._save_file_from_state(state)
                state.in_raw_mode = False
                return

            # Check for ===FILE: marker (explicit file format, no code block needed)
            if stripped.startswith(FILE_START_MARKER) and stripped.endswith("==="):
                filepath = stripped[len(FILE_START_MARKER):-3].strip()
                if filepath:
                    # Save previous file if exists
                    if state.current_file and state.file_content:
                        self._save_file_from_state(state)
                    state.current_file = filepath
                    state.file_content = []
                    state.in_code_block = False
                    state.in_raw_mode = True  # Using raw ===FILE:=== format
                return

            # If in raw mode (===FILE:=== format), accumulate everything until ===END_FILE===
            if state.in_raw_mode and state.current_file:
                state.file_content.append(cleaned_line)
                return

            # Check for code block end (```) while in a code block
            if state.in_code_block and self._is_code_block_end(cleaned_line):
                if state.current_file:
                    self._save_file_from_state(state)
                state.in_code_block = False
                return

            # Check for code block start (```)
            if stripped.startswith("```") and not state.in_code_block:
                state.in_code_block = True

                # Try to extract file path from code block line
                filepath = self._extract_filepath(cleaned_line)
                if filepath:
                    # Save previous file if exists
                    if state.current_file and state.file_content:
                        self._save_file_from_state(state)
                    state.current_file = filepath
                    state.file_content = []
                elif state.pending_file:
                    # Use pending file path
                    if state.current_file and state.file_content:
                        self._save_file_from_state(state)
                    state.current_file = state.pending_file
                    state.file_content = []
                    state.pending_file = None
                return

            # Try to extract file path from non-code-block line (for markdown formats)
            if not state.in_code_block and not state.current_file:
                filepath = self._extract_filepath(cleaned_line)
                if filepath:
                    # Store as pending, will be used when code block starts
                    state.pending_file = filepath
                    return

            # Accumulate content if we have a current file in code block mode
            if state.in_code_block and state.current_file is not None:
                state.file_content.append(cleaned_line)
            else:
                # Store non-file content in buffer
                self.buffer.append(cleaned_line)

    def _sanitize_requirements_txt(self, content: str) -> str:
        """Remove built-in Python modules from requirements.txt content."""
        # Python built-in modules that should NOT be in requirements.txt
        builtin_modules = {
            'sqlite3', 'os', 'sys', 'json', 're', 'math', 'datetime', 'time',
            'random', 'collections', 'itertools', 'functools', 'operator',
            'string', 'io', 'pathlib', 'typing', 'abc', 'enum', 'dataclasses',
            'copy', 'pickle', 'shelve', 'dbm', 'csv', 'configparser', 'argparse',
            'logging', 'warnings', 'traceback', 'unittest', 'doctest', 'pdb',
            'threading', 'multiprocessing', 'subprocess', 'socket', 'ssl',
            'email', 'html', 'xml', 'urllib', 'http', 'ftplib', 'smtplib',
            'uuid', 'hashlib', 'hmac', 'secrets', 'base64', 'binascii',
            'struct', 'codecs', 'locale', 'gettext', 'unicodedata',
            'tempfile', 'shutil', 'glob', 'fnmatch', 'linecache', 'stat',
            'fileinput', 'contextlib', 'weakref', 'types', 'gc', 'inspect',
            'dis', 'ast', 'ctypes', 'concurrent', 'asyncio', 'queue', 'heapq',
        }

        lines = content.split('\n')
        filtered_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                filtered_lines.append(line)
                continue
            # Extract package name (before ==, >=, <=, [, etc.)
            pkg_name = re.split(r'[=<>\[\s]', stripped)[0].lower()
            if pkg_name not in builtin_modules:
                filtered_lines.append(line)

        return '\n'.join(filtered_lines)

    def _save_file_from_state(self, state: AgentFileState) -> None:
        """Save the current file from agent state to disk."""
        if not state.current_file:
            return

        # Clean up the file path
        filepath = state.current_file.lstrip("/\\")
        target_path = self.output_dir / filepath

        # Create parent directories
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Write content
        content = "\n".join(state.file_content)
        # Remove leading/trailing empty lines but preserve internal structure
        content = content.strip()

        # Post-process requirements.txt to remove built-in modules
        if filepath.endswith('requirements.txt'):
            content = self._sanitize_requirements_txt(content)

        target_path.write_text(content, encoding="utf-8")
        self.saved_files.append(filepath)

        # Callback
        if self.on_file_saved:
            self.on_file_saved(filepath, len(content))

        # Reset state
        state.current_file = None
        state.file_content = []

    def get_remaining_content(self) -> str:
        """Get any content that wasn't part of a file block."""
        return "\n".join(self.buffer)

    def finalize(self) -> None:
        """Finalize parsing - save any incomplete files from all agents."""
        with self._lock:
            # Save incomplete files from all agent states
            for agent_name, state in self._agent_states.items():
                if state.current_file and state.file_content:
                    self._save_file_from_state(state)
                state.in_raw_mode = False
                state.in_code_block = False
            # Clear all agent states
            self._agent_states.clear()
