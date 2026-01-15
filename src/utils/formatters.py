"""Code formatters for auto-fixing generated code."""
import re
import subprocess
import shutil
from pathlib import Path
from typing import Callable, List


# Keywords that increase indentation for the next line
INDENT_KEYWORDS = {
    'def ', 'async def ', 'class ', 'if ', 'elif ', 'else:', 'for ', 'while ',
    'try:', 'except ', 'except:', 'finally:', 'with ', 'async with ', 'async for ',
    'match ', 'case ',
}


def fix_python_indentation(content: str, trust_existing: bool = False) -> str:
    """Fix missing indentation in Python code.

    This function adds proper 4-space indentation to Python code that was
    generated without indentation. It uses a two-pass approach:
    1. First pass: identify which lines should be at top level (indent 0)
    2. Second pass: apply indentation based on structure

    Args:
        content: Python source code, possibly without proper indentation
        trust_existing: If True, trust lines that already have indentation.
                       If False (default), recalculate all indentation.

    Returns:
        Python source code with proper indentation
    """
    lines = content.split('\n')

    # First pass: identify top-level lines
    # Top-level: imports, decorators followed by def/class, class definitions
    # BUT NOT: methods inside classes (def inside class body)
    top_level_indices = set()
    decorator_start = None
    in_class_body = False
    class_body_indent = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        # If line already has indentation and we're trusting it
        existing_indent = len(line) - len(line.lstrip())
        if existing_indent > 0 and trust_existing:
            # If we're in a class body and see indentation, continue tracking
            if in_class_body and existing_indent <= class_body_indent:
                in_class_body = False
            continue
        # Otherwise, analyze the stripped line content

        # Imports are always top-level
        if stripped.startswith(('import ', 'from ')):
            top_level_indices.add(i)
            in_class_body = False

        # Decorators at top level (not inside class)
        elif stripped.startswith('@'):
            if not in_class_body:
                if decorator_start is None:
                    decorator_start = i
                top_level_indices.add(i)

        # class definition is always top-level (unless nested, which is rare)
        elif stripped.startswith('class '):
            top_level_indices.add(i)
            decorator_start = None
            in_class_body = True  # Next lines are class body
            class_body_indent = 1  # Class body is at indent level 1

        # def: top-level only if NOT in class body
        elif stripped.startswith(('def ', 'async def ')):
            if not in_class_body:
                if decorator_start is not None:
                    top_level_indices.add(i)
                    decorator_start = None
                else:
                    top_level_indices.add(i)
            else:
                # Method inside class - don't mark as top-level
                decorator_start = None

        # Other statements: if we see them after class:, we're still in class body
        # until we see a new top-level construct
        else:
            decorator_start = None

    # Second pass: apply indentation
    result = []
    indent_level = 0
    paren_depth = 0
    bracket_depth = 0
    brace_depth = 0
    base_indent = 0  # Indent level before entering multiline expression
    function_body_indent = None  # Track function body indent level
    class_body_indent = None  # Track class body indent level
    prev_was_block_header = False  # Track if previous line ended with ':'
    prev_was_if_body = False  # Track if previous line was inside an if block body
    if_body_indent = None  # The indent level before entering the if block
    prev_was_block_ender = False  # Track if previous line was return/raise/break/continue

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Skip empty lines but reset tracking flags
        if not stripped:
            result.append('')
            prev_was_block_ender = False
            prev_was_block_header = False
            continue

        # Check if line already has indentation
        existing_indent = len(line) - len(line.lstrip())
        if existing_indent > 0 and trust_existing:
            # Trust existing indentation if flag is set
            result.append(line)
            indent_level = existing_indent // 4
            if stripped.endswith(':') and not stripped.startswith('#'):
                indent_level += 1
            continue
        # Otherwise, ignore existing indent and recalculate

        # Check if we're starting a multiline expression
        was_in_multiline = (paren_depth > 0 or bracket_depth > 0 or brace_depth > 0)

        # Track multi-line expressions - count before processing this line
        line_opens = stripped.count('(') + stripped.count('[') + stripped.count('{')
        line_closes = stripped.count(')') + stripped.count(']') + stripped.count('}')

        # If this is marked as top-level, reset indent
        if i in top_level_indices:
            indent_level = 0
            base_indent = 0
            function_body_indent = None  # Reset when at top level
            class_body_indent = None  # Reset when at top level

        # Track class body indent level
        if stripped.startswith('class '):
            class_body_indent = indent_level + 1
            function_body_indent = None  # Reset function tracking when entering a new class

        # Handle method/function definitions
        if stripped.startswith(('def ', 'async def ')):
            # If we're inside a class, reset to class body level for this method
            if class_body_indent is not None and indent_level > class_body_indent:
                indent_level = class_body_indent
            function_body_indent = indent_level + 1

        # After an if block's single statement body, dedent for subsequent lines
        # This makes statements after `if x: stmt` be at the same level as the if
        if prev_was_if_body and not prev_was_block_header and not was_in_multiline:
            is_block_continuation = stripped.startswith(('elif ', 'else:', 'except:', 'except ', 'finally:', 'case '))
            if not is_block_continuation and if_body_indent is not None:
                indent_level = if_body_indent
                prev_was_if_body = False

        # After return/raise/break/continue, dedent to function body level
        # because these statements end the current block's execution path
        # But NOT if we're at top-level (starting a new function/class)
        if prev_was_block_ender and not prev_was_block_header and not was_in_multiline:
            is_block_continuation = stripped.startswith(('elif ', 'else:', 'except:', 'except ', 'finally:', 'case '))
            is_top_level = i in top_level_indices
            if not is_block_continuation and not is_top_level and function_body_indent is not None:
                indent_level = function_body_indent
            prev_was_block_ender = False

        # Reset to function body level for standalone if statements:
        # When we see 'if' (not elif) that's not immediately after a block header,
        # reset to function body level. This makes consecutive ifs siblings.
        if not prev_was_block_header and not was_in_multiline:
            if stripped.startswith('if '):
                # This is a standalone 'if', make it a sibling at function body level
                if function_body_indent is not None and indent_level > function_body_indent:
                    indent_level = function_body_indent

        # Handle else/elif/except/finally - dedent first
        if stripped.startswith(('else:', 'elif ', 'except:', 'except ', 'finally:', 'case ')):
            indent_level = max(0, indent_level - 1)

        # Determine indent for this line
        if was_in_multiline:
            # Inside multiline - use increased indent
            current_indent = base_indent + 1
        else:
            current_indent = indent_level

        # Add the line with proper indentation
        result.append('    ' * current_indent + stripped)

        # Update paren tracking AFTER processing the line
        for char in stripped:
            if char == '(':
                if paren_depth == 0 and bracket_depth == 0 and brace_depth == 0:
                    base_indent = indent_level
                paren_depth += 1
            elif char == ')':
                paren_depth = max(0, paren_depth - 1)
            elif char == '[':
                if paren_depth == 0 and bracket_depth == 0 and brace_depth == 0:
                    base_indent = indent_level
                bracket_depth += 1
            elif char == ']':
                bracket_depth = max(0, bracket_depth - 1)
            elif char == '{':
                if paren_depth == 0 and bracket_depth == 0 and brace_depth == 0:
                    base_indent = indent_level
                brace_depth += 1
            elif char == '}':
                brace_depth = max(0, brace_depth - 1)

        in_multiline = (paren_depth > 0 or bracket_depth > 0 or brace_depth > 0)

        # If we just closed a multiline, reset to base indent
        if was_in_multiline and not in_multiline:
            indent_level = base_indent

        # Decorators don't change indentation for next line
        if stripped.startswith('@'):
            continue

        # Lines ending with colon increase indent for next line
        if stripped.endswith(':') and not stripped.startswith('#') and not in_multiline:
            indent_level += 1
            # Track if we're entering an if block (for single-statement body detection)
            if stripped.startswith('if '):
                if_body_indent = indent_level - 1  # The level of the if statement itself

        # Track if this line was inside an if body (the single statement after if:)
        if prev_was_block_header and stripped.startswith('if '):
            # Previous line was the if:, this line is NOT the body (it's another if)
            prev_was_if_body = False
        elif prev_was_block_header:
            # Previous line was a : line, check if it was an if
            # We'll set this flag for the NEXT iteration to detect
            prev_was_if_body = True
        elif not stripped.endswith(':'):
            # Regular statement, if we were tracking if body, keep it for one more line
            pass
        else:
            prev_was_if_body = False

        # Track if this line ended with ':' for next iteration
        prev_was_block_header = stripped.endswith(':') and not stripped.startswith('#') and not in_multiline

        # Track if this line was a block-ending statement (return/raise/break/continue)
        block_enders = ('return', 'return ', 'raise ', 'raise(', 'break', 'continue')
        prev_was_block_ender = any(stripped.startswith(be) or stripped == be.strip() for be in block_enders)

    return '\n'.join(result)


def fix_js_indentation(content: str, indent_size: int = 2) -> str:
    """Fix missing indentation in JavaScript/TypeScript code.

    This function adds proper indentation to JS/TS code that was
    generated without indentation. It tracks brace depth to determine
    the correct indentation level.

    Args:
        content: JavaScript/TypeScript source code, possibly without proper indentation
        indent_size: Number of spaces per indent level (default 2 for JS)

    Returns:
        JavaScript/TypeScript source code with proper indentation
    """
    lines = content.split('\n')
    result = []
    indent_level = 0

    # Track if we're inside a string (to avoid counting braces in strings)
    in_string = False
    string_char = None

    for line in lines:
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            result.append('')
            continue

        # Check if line already has indentation - if so, trust it
        existing_indent = len(line) - len(line.lstrip())
        if existing_indent > 0:
            result.append(line)
            # Update indent level based on braces in this line
            open_braces = stripped.count('{') + stripped.count('[') + stripped.count('(')
            close_braces = stripped.count('}') + stripped.count(']') + stripped.count(')')
            indent_level = existing_indent // indent_size
            indent_level += open_braces - close_braces
            indent_level = max(0, indent_level)
            continue

        # Count opening and closing braces (simplified - doesn't handle strings perfectly)
        open_braces = stripped.count('{') + stripped.count('[') + stripped.count('(')
        close_braces = stripped.count('}') + stripped.count(']') + stripped.count(')')

        # If line starts with closing brace, dedent first
        if stripped[0] in '}])':
            indent_level = max(0, indent_level - 1)

        # Add the line with proper indentation
        result.append(' ' * (indent_size * indent_level) + stripped)

        # Update indent level for next line
        # Net change = opens - closes, but we already dedented for leading close
        net_change = open_braces - close_braces
        if stripped[0] in '}])':
            # We already dedented, so add back one for the leading close we counted
            net_change += 1

        indent_level += net_change
        indent_level = max(0, indent_level)

    return '\n'.join(result)


def fix_pydantic_config(content: str) -> str:
    """Fix Pydantic Config class that's wrongly placed outside Response class.

    The LLM and indentation fixer often produce:
        class UserResponse(BaseModel):
            id: int

        class Config:  # WRONG - outside class
            from_attributes = True

    This should be:
        class UserResponse(BaseModel):
            id: int

            class Config:  # CORRECT - inside class
                from_attributes = True
    """
    lines = content.split('\n')
    fixed_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Check if this is a standalone "class Config:" at column 0
        if stripped.startswith('class Config:') and not line.startswith(' ') and not line.startswith('\t'):
            # Look back to find the Response class this should belong to
            for j in range(len(fixed_lines) - 1, -1, -1):
                prev_line = fixed_lines[j].strip()
                if prev_line.startswith('class ') and 'Response' in prev_line:
                    # Found a Response class - indent this Config and its body
                    if fixed_lines and fixed_lines[-1].strip():
                        fixed_lines.append('')
                    fixed_lines.append('    class Config:')

                    # Indent all following lines that are part of Config
                    i += 1
                    while i < len(lines):
                        next_line = lines[i]
                        next_stripped = next_line.strip()

                        # Stop if we hit another class definition
                        if next_stripped.startswith('class ') and not next_stripped.startswith('class Config'):
                            i -= 1
                            break

                        # Stop if we hit a non-indented non-empty line (not part of Config)
                        if next_stripped and not next_line.startswith(' ') and not next_line.startswith('\t'):
                            if not next_stripped.startswith('from_attributes') and not next_stripped.startswith('orm_mode'):
                                i -= 1
                                break

                        # Indent the content
                        if next_stripped:
                            fixed_lines.append('        ' + next_stripped)
                        else:
                            fixed_lines.append('')
                        i += 1
                    break
            else:
                # No Response class found, keep as is
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)
        i += 1

    return '\n'.join(fixed_lines)


def fix_settings_instantiation(content: str) -> str:
    """Fix Settings() instantiation that's wrongly placed inside Settings class."""
    lines = content.split('\n')
    fixed_lines = []
    settings_line = None
    in_settings_class = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith('class Settings'):
            in_settings_class = True
            fixed_lines.append(line)
            continue

        if in_settings_class and stripped.startswith('class ') and not line.startswith(' ') and not line.startswith('\t'):
            in_settings_class = False

        if in_settings_class and stripped == 'settings = Settings()' and (line.startswith(' ') or line.startswith('\t')):
            settings_line = 'settings = Settings()'
            continue

        fixed_lines.append(line)

    if settings_line:
        if fixed_lines and fixed_lines[-1].strip():
            fixed_lines.append('')
        fixed_lines.append('')
        fixed_lines.append(settings_line)

    return '\n'.join(fixed_lines)


def fix_yaml_indentation(content: str) -> str:
    """Fix missing indentation in YAML files (docker-compose.yml, ci.yml).

    YAML uses 2-space indentation where each nested level adds 2 spaces.
    This function reconstructs proper indentation based on YAML structure.
    """
    lines = content.split('\n')
    result = []
    indent_stack = [0]  # Stack of indent levels

    # Top-level keys that should have 0 indent
    top_level_keys = {
        'version', 'services', 'volumes', 'networks', 'name', 'on', 'jobs',
        'env', 'defaults', 'permissions', 'concurrency'
    }

    # Keys that indicate a new nested block (their children need more indent)
    block_keys = {
        'services', 'volumes', 'networks', 'on', 'jobs', 'steps', 'env',
        'build', 'environment', 'ports', 'depends_on', 'with', 'strategy',
        'matrix', 'container', 'options', 'outputs', 'inputs', 'secrets'
    }

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            result.append('')
            i += 1
            continue

        # Skip comments but preserve them at current indent
        if stripped.startswith('#'):
            current_indent = indent_stack[-1] if indent_stack else 0
            result.append('  ' * current_indent + stripped)
            i += 1
            continue

        # Check if this is a list item (starts with -)
        is_list_item = stripped.startswith('-')

        # Extract the key if this is a key: value line
        key = None
        if ':' in stripped and not is_list_item:
            key = stripped.split(':')[0].strip()
        elif is_list_item and ':' in stripped:
            # List item with key like "- name: something"
            after_dash = stripped[1:].strip()
            if ':' in after_dash:
                key = after_dash.split(':')[0].strip()

        # Determine the correct indent level
        if key and key in top_level_keys:
            # Top-level keys always at indent 0
            indent_stack = [0]
            result.append(stripped)
        elif is_list_item:
            # List items: use current indent level
            current_indent = indent_stack[-1] if indent_stack else 0
            result.append('  ' * current_indent + stripped)

            # If list item has nested content (like steps), push indent
            if stripped.endswith(':'):
                indent_stack.append(current_indent + 2)
        elif key:
            # Key: value line
            current_indent = indent_stack[-1] if indent_stack else 0

            # Check if previous non-empty line was a block key ending with :
            # If so, this should be nested under it
            prev_was_block = False
            for j in range(len(result) - 1, -1, -1):
                prev_stripped = result[j].strip()
                if prev_stripped:
                    if prev_stripped.endswith(':') and not prev_stripped.startswith('-'):
                        prev_was_block = True
                    break

            if prev_was_block and current_indent > 0:
                # Already at correct level from previous block
                pass
            elif key in block_keys:
                # Block keys at current level
                pass

            result.append('  ' * current_indent + stripped)

            # If this line ends with :, next level needs more indent
            if stripped.endswith(':'):
                indent_stack.append(current_indent + 1)
        else:
            # Other lines (values, etc.)
            current_indent = indent_stack[-1] if indent_stack else 0
            result.append('  ' * current_indent + stripped)

        i += 1

    return '\n'.join(result)


def fix_docker_compose_yaml(content: str) -> str:
    """Fix docker-compose.yml specific indentation.

    Docker-compose structure:
    version: '3.8'        # 0 indent
    services:             # 0 indent
      backend:            # 2 spaces (service name)
        build:            # 4 spaces (service config)
          context: ./x    # 6 spaces (build config)
        ports:            # 4 spaces
          - "8000:8000"   # 6 spaces (list item)
    volumes:              # 0 indent
      data:               # 2 spaces
    networks:             # 0 indent
      app-network:        # 2 spaces
        driver: bridge    # 4 spaces
    """
    lines = content.split('\n')
    result = []

    # Top-level ONLY keys (never appear inside services)
    top_level_only_keys = {'version', 'services'}

    # Keys that can be both top-level AND service-level
    # We need lookahead to decide
    ambiguous_keys = {'volumes', 'networks'}

    # Service-level keys (directly under service name)
    service_keys = {
        'build', 'ports', 'environment', 'volumes', 'networks', 'depends_on',
        'image', 'container_name', 'restart', 'command', 'expose', 'labels',
        'healthcheck', 'deploy', 'logging', 'ulimits', 'sysctls', 'cap_add',
        'cap_drop', 'devices', 'dns', 'entrypoint', 'env_file', 'extra_hosts',
        'hostname', 'init', 'ipc', 'isolation', 'links', 'network_mode', 'pid',
        'platform', 'privileged', 'profiles', 'pull_policy', 'read_only',
        'runtime', 'scale', 'security_opt', 'shm_size', 'stdin_open',
        'stop_grace_period', 'stop_signal', 'storage_opt', 'tmpfs', 'tty',
        'user', 'userns_mode', 'working_dir'
    }

    # Keys that are nested under 'build:'
    build_keys = {'context', 'dockerfile', 'args', 'target', 'cache_from', 'network', 'labels'}

    # Helper: look ahead to see if next non-empty line starts with '-' (list item)
    def next_is_list_item(idx):
        for j in range(idx + 1, len(lines)):
            next_stripped = lines[j].strip()
            if next_stripped:
                return next_stripped.startswith('-')
        return False

    # Track context
    section = None  # 'services', 'volumes', 'networks'
    in_service = False  # Inside a service definition
    in_build = False  # Inside build: block

    for i, line in enumerate(lines):
        stripped = line.strip()

        if not stripped:
            result.append('')
            continue

        # Extract key if this is a key: line
        key = None
        if ':' in stripped:
            key = stripped.split(':')[0].strip()

        # Check for top-level ONLY keys (0 indent) - always top-level
        if key and key in top_level_only_keys:
            result.append(stripped)
            section = key
            in_service = False
            in_build = False
            continue

        # Handle ambiguous keys (volumes:, networks:)
        # If followed by list item -> service-level
        # If followed by a name ending with : -> top-level section
        if key and key in ambiguous_keys and stripped == f'{key}:':
            if section == 'services' and in_service:
                # Check next line to decide
                if next_is_list_item(i):
                    # Service-level: volumes: or networks: with list items
                    result.append('    ' + stripped)  # 4 spaces (service level)
                    in_build = False
                    continue
            # Top-level section
            result.append(stripped)
            section = key
            in_service = False
            in_build = False
            continue

        # Handle services section
        if section == 'services':
            # Service name detection: ends with : and no other colons, and key is NOT a service_key
            is_service_name = (
                stripped.endswith(':') and
                stripped.count(':') == 1 and
                key and key not in service_keys and key not in build_keys
            )

            if is_service_name:
                result.append('  ' + stripped)  # 2 spaces - service name
                in_service = True
                in_build = False
                continue

            if in_service:
                # Check if this is a build: key
                if key == 'build':
                    result.append('    ' + stripped)  # 4 spaces
                    in_build = stripped.endswith(':')  # Only if it's "build:" not "build: ./dir"
                    continue

                # Check if this is under build:
                if in_build and key in build_keys:
                    result.append('      ' + stripped)  # 6 spaces
                    continue

                # Service-level keys reset in_build
                if key in service_keys:
                    result.append('    ' + stripped)  # 4 spaces
                    in_build = False
                    continue

                # List items
                if stripped.startswith('-'):
                    result.append('      ' + stripped)  # 6 spaces
                    continue

                # Other content inside service
                if in_build:
                    result.append('      ' + stripped)  # 6 spaces (under build)
                else:
                    result.append('    ' + stripped)  # 4 spaces (under service)
                continue

        # Handle volumes section
        if section == 'volumes':
            # Volume name: ends with : only
            if stripped.endswith(':') and stripped.count(':') == 1:
                result.append('  ' + stripped)  # 2 spaces
            else:
                result.append('    ' + stripped)  # 4 spaces
            continue

        # Handle networks section
        if section == 'networks':
            # Network name: ends with : only
            if stripped.endswith(':') and stripped.count(':') == 1:
                result.append('  ' + stripped)  # 2 spaces
            else:
                result.append('    ' + stripped)  # 4 spaces
            continue

        # Fallback
        result.append(stripped)

    return '\n'.join(result)


def fix_github_actions_yaml(content: str) -> str:
    """Fix GitHub Actions ci.yml specific indentation.

    GitHub Actions structure:
    name: CI               # 0 indent
    on:                    # 0 indent
      push:                # 2 spaces
        branches: [main]   # 4 spaces
    jobs:                  # 0 indent
      test:                # 2 spaces (job name)
        runs-on: ubuntu    # 4 spaces
        services:          # 4 spaces
          postgres:        # 6 spaces
            image: x       # 8 spaces
        steps:             # 4 spaces
          - uses: x        # 6 spaces (list item)
          - name: y        # 6 spaces
            with:          # 8 spaces
              key: value   # 10 spaces
            run: z         # 8 spaces (under list item key)
    """
    lines = content.split('\n')
    result = []

    # Job-level keys (directly under job name)
    job_keys = {
        'runs-on', 'needs', 'if', 'steps', 'services', 'container', 'env',
        'environment', 'outputs', 'strategy', 'timeout-minutes', 'continue-on-error',
        'permissions', 'concurrency', 'defaults', 'uses', 'with', 'secrets'
    }

    # Service-level keys (under services.service_name)
    service_keys = {'image', 'ports', 'env', 'options', 'volumes', 'credentials'}

    # Step item keys (under each - item in steps)
    step_item_keys = {'uses', 'with', 'run', 'name', 'id', 'if', 'env', 'continue-on-error', 'timeout-minutes', 'shell', 'working-directory'}

    # Keys under 'with:'
    with_keys = {'python-version', 'node-version', 'go-version', 'java-version', 'cache', 'fetch-depth'}

    # Track context
    section = None  # 'on', 'jobs', 'env', etc.
    in_job = False
    in_services = False
    in_service = False
    in_service_env = False  # Inside env: block within a service
    in_steps = False
    in_step_item = False
    in_with = False
    in_strategy = False
    in_matrix = False

    for i, line in enumerate(lines):
        stripped = line.strip()

        if not stripped:
            result.append('')
            continue

        # Extract key
        key = None
        if ':' in stripped and not stripped.startswith('-'):
            key = stripped.split(':')[0].strip()

        # Top-level keys
        if stripped.startswith('name:'):
            result.append(stripped)
            section = None
            in_job = in_services = in_service = in_steps = in_step_item = in_with = False
            continue

        if stripped == 'on:':
            result.append('on:')
            section = 'on'
            in_job = in_services = in_steps = False
            continue

        if stripped == 'jobs:':
            result.append('jobs:')
            section = 'jobs'
            in_job = in_services = in_steps = False
            continue

        if stripped == 'env:' and section is None:
            result.append('env:')
            section = 'env'
            continue

        if stripped == 'permissions:' and section is None:
            result.append('permissions:')
            section = 'permissions'
            continue

        # Inside 'on:' section
        if section == 'on':
            if stripped in ['push:', 'pull_request:', 'workflow_dispatch:', 'schedule:', 'release:']:
                result.append('  ' + stripped)
                continue
            if ':' in stripped or stripped.startswith('-'):
                result.append('    ' + stripped)
                continue

        # Inside 'env:' or 'permissions:' section (top-level)
        if section in ['env', 'permissions']:
            result.append('  ' + stripped)
            continue

        # Inside 'jobs:' section
        if section == 'jobs':
            # First check if we're inside a job's sub-sections (before checking for new job)
            if in_job:
                # Handle steps:
                if stripped == 'steps:':
                    result.append('    steps:')  # 4 spaces
                    in_steps = True
                    in_step_item = False
                    in_services = in_service = in_with = in_strategy = in_matrix = False
                    continue

                # Handle services:
                if stripped == 'services:':
                    result.append('    services:')  # 4 spaces
                    in_services = True
                    in_steps = in_step_item = in_with = in_strategy = in_matrix = False
                    continue

                # Handle strategy:
                if stripped == 'strategy:':
                    result.append('    strategy:')  # 4 spaces
                    in_strategy = True
                    in_steps = in_services = in_with = in_matrix = False
                    continue

                # Inside strategy
                if in_strategy:
                    if stripped == 'matrix:':
                        result.append('      matrix:')  # 6 spaces
                        in_matrix = True
                        continue
                    if in_matrix:
                        result.append('        ' + stripped)  # 8 spaces
                        continue
                    result.append('      ' + stripped)  # 6 spaces
                    continue

                # Inside services section (must check before job name detection!)
                if in_services:
                    # Service name (postgres:, redis:, sqlite:, etc.)
                    if stripped.endswith(':') and stripped.count(':') == 1 and key not in service_keys:
                        result.append('      ' + stripped)  # 6 spaces - service name
                        in_service = True
                        in_service_env = False
                        continue
                    if in_service:
                        # Check if this is env: block
                        if stripped == 'env:':
                            result.append('        env:')  # 8 spaces
                            in_service_env = True
                            continue
                        # Content inside env: block (env vars like POSTGRES_PASSWORD: value)
                        if in_service_env:
                            if key in service_keys and key != 'env':
                                # New service key, exit env block
                                in_service_env = False
                                result.append('        ' + stripped)  # 8 spaces
                            else:
                                result.append('          ' + stripped)  # 10 spaces (env var)
                            continue
                        # Service config (image:, ports:, etc.)
                        if key in service_keys:
                            result.append('        ' + stripped)  # 8 spaces
                            continue
                        if stripped.startswith('-'):
                            result.append('          ' + stripped)  # 10 spaces (list items)
                            continue
                        result.append('        ' + stripped)  # 8 spaces
                        continue
                    result.append('      ' + stripped)  # 6 spaces
                    continue

                # Inside steps
                if in_steps:
                    # Check if this looks like a new job name (escape hatch)
                    # A new job name: ends with :, single colon, not a step key
                    looks_like_job = (
                        stripped.endswith(':') and
                        stripped.count(':') == 1 and
                        key and key not in job_keys and key not in service_keys and
                        key not in step_item_keys and
                        not stripped.startswith('-')
                    )
                    if looks_like_job:
                        # This is a new job, escape from steps
                        result.append('  ' + stripped)  # 2 spaces - job name
                        in_job = True
                        in_services = in_service = in_steps = in_step_item = in_with = in_strategy = in_matrix = False
                        continue

                    # Step list item (- uses:, - name:, etc.)
                    if stripped.startswith('-'):
                        result.append('      ' + stripped)  # 6 spaces
                        in_step_item = True
                        in_with = False
                        continue

                    if in_step_item:
                        # with: under step item
                        if stripped == 'with:':
                            result.append('        with:')  # 8 spaces
                            in_with = True
                            continue

                        # Content under with:
                        if in_with:
                            result.append('          ' + stripped)  # 10 spaces
                            # Exit with: when we see another step key
                            if key in step_item_keys and key != 'with':
                                in_with = False
                            continue

                        # Other step item content (run:, uses:, env:, etc.)
                        result.append('        ' + stripped)  # 8 spaces
                        # Exit with: mode when we see step keys
                        if key in step_item_keys:
                            in_with = False
                        continue

                # Job-level keys (runs-on:, needs:, etc.)
                if key in job_keys:
                    result.append('    ' + stripped)  # 4 spaces
                    continue

            # Detect job name: single word ending with : that's not a job_key
            is_job_name = (
                stripped.endswith(':') and
                stripped.count(':') == 1 and
                key and key not in job_keys and key not in service_keys
            )

            if is_job_name:
                result.append('  ' + stripped)  # 2 spaces - job name
                in_job = True
                in_services = in_service = in_steps = in_step_item = in_with = in_strategy = in_matrix = False
                continue

            # Fallback for job content - unknown keys get job-level indent
            if in_job:
                result.append('    ' + stripped)  # 4 spaces
                continue

        # Fallback
        result.append(stripped)

    return '\n'.join(result)


def format_yaml_file(filepath: Path) -> bool:
    """Format a YAML file with proper indentation.

    Returns True if formatting was successful, False otherwise.
    """
    try:
        content = filepath.read_text(encoding='utf-8')
        filename = filepath.name.lower()

        if 'docker-compose' in filename or 'compose' in filename:
            fixed_content = fix_docker_compose_yaml(content)
        elif 'ci' in filename or 'workflow' in filename or '.github' in str(filepath).lower():
            fixed_content = fix_github_actions_yaml(content)
        else:
            # Generic YAML fix
            fixed_content = fix_yaml_indentation(content)

        filepath.write_text(fixed_content, encoding='utf-8')
        return True
    except Exception:
        return False


def format_python_file(filepath: Path) -> bool:
    """Format a Python file - first fix indentation, then run black.

    Returns True if formatting was successful, False otherwise.
    """
    try:
        # Read the file
        content = filepath.read_text(encoding='utf-8')

        # First, fix indentation
        fixed_content = fix_python_indentation(content)

        # Apply Pydantic/Settings fixes for schema and config files
        filepath_str = str(filepath).lower()
        if 'schema' in filepath_str:
            fixed_content = fix_pydantic_config(fixed_content)
        if 'config' in filepath_str or 'settings' in filepath_str:
            fixed_content = fix_settings_instantiation(fixed_content)

        # Write back the fixed content
        filepath.write_text(fixed_content, encoding='utf-8')

        # Then try to run black for additional formatting
        black_path = shutil.which("black")
        if black_path:
            try:
                subprocess.run(
                    [black_path, str(filepath), "--quiet"],
                    capture_output=True,
                    text=True,
                    timeout=10  # Reduced timeout - formatting should be fast
                )
            except subprocess.TimeoutExpired:
                pass  # Skip if timeout
            except Exception:
                pass  # Black formatting is optional

        return True
    except Exception:
        return False


def format_js_file(filepath: Path) -> bool:
    """Format a JavaScript/TypeScript/JSON file.

    First fixes indentation using our custom indenter, then runs prettier if available.

    Returns True if formatting was successful, False otherwise.
    """
    try:
        # Read the file
        content = filepath.read_text(encoding='utf-8')

        # First, fix indentation (skip for JSON files as they have different structure)
        suffix = filepath.suffix.lower()
        if suffix != '.json':
            fixed_content = fix_js_indentation(content)
            filepath.write_text(fixed_content, encoding='utf-8')

        # Then try to run prettier for additional formatting
        # Only use direct prettier, NOT npx (npx can hang trying to download)
        prettier_path = shutil.which("prettier")

        if prettier_path:
            try:
                subprocess.run(
                    [prettier_path, "--write", str(filepath)],
                    capture_output=True,
                    text=True,
                    timeout=10  # Reduced timeout - formatting should be fast
                )
            except subprocess.TimeoutExpired:
                pass  # Skip if timeout
            except Exception:
                pass  # Prettier formatting is optional

        return True
    except Exception:
        return False


def format_file(filepath: Path, on_formatted: Callable[[str, bool], None] | None = None) -> bool:
    """Auto-format a file based on its extension.

    Args:
        filepath: Path to the file to format
        on_formatted: Optional callback(filepath, success) called after formatting

    Returns:
        True if formatting was successful or not needed, False if it failed
    """
    suffix = filepath.suffix.lower()
    filename = filepath.name.lower()
    success = True

    # Python files
    if suffix == ".py":
        success = format_python_file(filepath)

    # YAML files (docker-compose.yml, ci.yml, etc.)
    elif suffix in (".yml", ".yaml"):
        success = format_yaml_file(filepath)

    # JavaScript/TypeScript files
    elif suffix in (".js", ".jsx", ".ts", ".tsx", ".json", ".css", ".scss", ".html", ".vue", ".svelte"):
        success = format_js_file(filepath)

    if on_formatted:
        on_formatted(str(filepath), success)

    return success


def format_project(project_dir: Path, on_progress: Callable[[str, bool], None] | None = None) -> dict:
    """Format all files in a project directory.

    Args:
        project_dir: Path to the project directory
        on_progress: Optional callback(filepath, success) called for each file

    Returns:
        Dictionary with counts: {"formatted": N, "failed": N, "skipped": N}
    """
    stats = {"formatted": 0, "failed": 0, "skipped": 0}

    # Extensions to format
    python_exts = {".py"}
    js_exts = {".js", ".jsx", ".ts", ".tsx", ".json", ".css", ".scss", ".html", ".vue", ".svelte"}
    yaml_exts = {".yml", ".yaml"}
    all_exts = python_exts | js_exts | yaml_exts

    for filepath in project_dir.rglob("*"):
        if not filepath.is_file():
            continue

        suffix = filepath.suffix.lower()
        if suffix not in all_exts:
            stats["skipped"] += 1
            continue

        # Skip node_modules and virtual environments
        path_str = str(filepath)
        if "node_modules" in path_str or "venv" in path_str or ".venv" in path_str:
            stats["skipped"] += 1
            continue

        success = format_file(filepath, on_progress)
        if success:
            stats["formatted"] += 1
        else:
            stats["failed"] += 1

    return stats


def check_formatters_available() -> dict:
    """Check which formatters are available on the system.

    Returns:
        Dictionary with formatter names and their availability
    """
    return {
        "black": shutil.which("black") is not None,
        # Only check direct prettier, NOT npx (npx can hang trying to download)
        "prettier": shutil.which("prettier") is not None,
        "python_indenter": True,  # Our custom Python indenter is always available
        "js_indenter": True,  # Our custom JS/TS indenter is always available
        "yaml_indenter": True,  # Our custom YAML indenter is always available
    }
