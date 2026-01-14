"""LLM wrapper supporting multiple providers: Qwen CLI and OpenAI API."""
import os
import subprocess
import sys
import threading
from abc import ABC, abstractmethod
from typing import Callable

from dotenv import load_dotenv

load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


class LLMResponse:
    """Simple response wrapper to match LangChain API."""
    def __init__(self, content: str):
        self.content = content


class BaseLLM(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self):
        self.status_callback: Callable[[str], None] | None = None
        self._lock = threading.Lock()  # Lock for thread-safe access
        # Use thread-local storage for current_agent to avoid race conditions
        self._thread_local = threading.local()

    @property
    def current_agent(self) -> str | None:
        """Get current agent name (thread-local)."""
        return getattr(self._thread_local, 'agent_name', None)

    @current_agent.setter
    def current_agent(self, value: str | None):
        """Set current agent name (thread-local)."""
        self._thread_local.agent_name = value

    def set_current_agent(self, agent_name: str | None):
        """Set the current agent name for logging purposes (thread-safe)."""
        self.current_agent = agent_name

    def set_status_callback(self, callback: Callable[[str], None] | None):
        """Set the callback for status updates."""
        self.status_callback = callback

    def _notify_status(self, message: str):
        """Notify the callback with a status message."""
        if not message or self.status_callback is None:
            return
        try:
            if self.current_agent:
                message = f"[{self.current_agent}] {message}"
            self.status_callback(message)
        except Exception:
            pass

    @abstractmethod
    def invoke(self, messages) -> LLMResponse:
        """Invoke the LLM with the given messages."""
        pass


class LocalQwenLLM(BaseLLM):
    """LLM wrapper that uses local Qwen CLI for inference."""

    def __init__(
        self,
        command: str | None = None,
        model: str | None = None,
        timeout: int | None = None,
    ):
        super().__init__()
        self.command = command or os.getenv("QWEN_CLI_COMMAND", "qwen")
        self.model = model or os.getenv("QWEN_MODEL")
        # timeout=0 means wait until done (no timeout)
        self.timeout = timeout if timeout is not None else int(os.getenv("QWEN_TIMEOUT", "0"))

    def invoke(self, messages) -> LLMResponse:
        """Invoke the LLM with the given messages."""
        prompt = "\n".join(
            m.content for m in messages if getattr(m, "content", None)
        ).strip()

        if not prompt:
            raise ValueError("LocalQwenLLM received an empty prompt.")

        agent_name = self.current_agent or "Unknown"
        self._notify_status(f">>> Starting {agent_name} (prompt: {len(prompt)} chars)...")

        output = self._run_qwen(prompt)

        self._notify_status(f">>> {agent_name} completed (output: {len(output)} chars)")

        return LLMResponse(output)

    def _run_qwen(self, prompt: str) -> str:
        """Run the Qwen CLI with the given prompt."""
        args = ["cmd", "/c", self.command]
        if self.model:
            args.extend(["-m", self.model])
        args.extend(["--output-format", "text"])

        try:
            with subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace'
            ) as process:
                output_lines = []

                if process.stdout is None or process.stdin is None:
                    raise RuntimeError("Unable to capture Qwen CLI streams.")

                process.stdin.write(prompt)
                process.stdin.flush()
                process.stdin.close()

                for line in process.stdout:
                    cleaned = line.rstrip("\r\n")
                    output_lines.append(cleaned)
                    self._notify_status(cleaned)

                # timeout=0 means wait indefinitely until process finishes
                wait_timeout = self.timeout if self.timeout > 0 else None
                try:
                    process.wait(timeout=wait_timeout)
                except subprocess.TimeoutExpired as exc:
                    process.kill()
                    raise RuntimeError(
                        f"Qwen CLI timed out after {self.timeout} seconds."
                    ) from exc

                if process.returncode != 0:
                    raise RuntimeError("Qwen CLI error: non-zero exit code.")

            return "\n".join(output_lines).strip()

        except FileNotFoundError as exc:
            raise RuntimeError(
                f"Failed to invoke Qwen CLI ({self.command}): {exc}"
            ) from exc


class OpenAILLM(BaseLLM):
    """LLM wrapper that uses OpenAI API for inference."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ):
        super().__init__()
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")  # For custom endpoints
        self.temperature = temperature if temperature is not None else float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
        self.max_tokens = max_tokens if max_tokens is not None else int(os.getenv("OPENAI_MAX_TOKENS", "4096"))
        self._client = None

    def _get_client(self):
        """Lazy initialize OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError(
                    "openai package not installed. Run: pip install openai"
                )

            if not self.api_key:
                raise ValueError(
                    "OPENAI_API_KEY not set. Add it to .env file or environment."
                )

            client_kwargs = {"api_key": self.api_key}
            if self.base_url:
                client_kwargs["base_url"] = self.base_url

            self._client = OpenAI(**client_kwargs)
        return self._client

    def invoke(self, messages) -> LLMResponse:
        """Invoke the LLM with the given messages."""
        prompt = "\n".join(
            m.content for m in messages if getattr(m, "content", None)
        ).strip()

        if not prompt:
            raise ValueError("OpenAILLM received an empty prompt.")

        agent_name = self.current_agent or "Unknown"
        self._notify_status(f">>> Starting {agent_name} (prompt: {len(prompt)} chars)...")

        output = self._call_openai(prompt)

        self._notify_status(f">>> {agent_name} completed (output: {len(output)} chars)")

        return LLMResponse(output)

    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API with streaming."""
        client = self._get_client()

        output_lines = []

        try:
            # Use streaming for real-time output
            stream = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
            )

            current_line = ""
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content

                    # Process character by character to handle newlines
                    for char in content:
                        if char == "\n":
                            if current_line:
                                output_lines.append(current_line)
                                self._notify_status(current_line)
                            current_line = ""
                        else:
                            current_line += char

            # Don't forget the last line if it doesn't end with newline
            if current_line:
                output_lines.append(current_line)
                self._notify_status(current_line)

            return "\n".join(output_lines).strip()

        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {str(e)}") from e


def create_llm() -> BaseLLM:
    """Factory function to create the appropriate LLM based on configuration."""
    provider = os.getenv("LLM_PROVIDER", "qwen").lower()

    if provider == "openai":
        return OpenAILLM()
    elif provider == "qwen":
        return LocalQwenLLM()
    else:
        raise ValueError(f"Unknown LLM provider: {provider}. Use 'qwen' or 'openai'.")


# Global LLM instance - created based on LLM_PROVIDER env var
llm = create_llm()
