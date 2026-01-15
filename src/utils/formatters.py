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
    success = True

    # Python files
    if suffix == ".py":
        success = format_python_file(filepath)

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
    all_exts = python_exts | js_exts

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
    }
