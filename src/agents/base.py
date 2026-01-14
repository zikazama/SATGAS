"""
Base Agent Module
=================

Modul ini berisi base class untuk semua agent dalam SATGAS framework.
Gunakan class ini sebagai parent class saat membuat agent baru.

CARA MEMBUAT AGENT BARU:
------------------------

1. Buat file baru di folder src/agents/ (contoh: my_agent.py)

2. Import dan extend BaseAgent:

   from .base import BaseAgent

   class MyAgent(BaseAgent):
       # Definisikan metadata agent
       agent_id = "my_agent"           # ID unik, akan digunakan di workflow
       agent_name = "My Agent"         # Nama untuk display di UI
       display_name = "My Agent"       # Nama yang ditampilkan ke LLM
       step_order = 9                  # Urutan eksekusi (1-based)
       description = "Deskripsi agent" # Deskripsi singkat
       color = "#FF5722"               # Warna untuk UI (hex)

       # Field yang akan diisi oleh agent ini ke state
       output_fields = [
           ("my_output", "my_output.json", "json"),
       ]

       # Field yang dibutuhkan dari state (opsional)
       required_fields = ["spec"]

       def build_prompt(self, state):
           '''Bangun prompt untuk LLM berdasarkan state.'''
           return f'''
           Kamu adalah {self.agent_name}.

           TUGAS:
           ...

           INPUT:
           {state.get("spec", "")}
           '''

       def process_response(self, state, response):
           '''Proses response dari LLM dan update state.'''
           state["my_output"] = response.content
           state["status"] = "my_agent_done"
           return state

3. Daftarkan agent di src/agents/registry.py:

   from .my_agent import MyAgent

   # Tambahkan ke AGENT_CLASSES
   AGENT_CLASSES = [
       ...
       MyAgent,
   ]

4. Tambahkan field output ke state di src/core/state.py jika belum ada

5. Update config/settings.py AGENTS_CONFIG jika ingin kustomisasi UI


LIFECYCLE AGENT:
----------------

1. Agent di-instantiate saat registry dimuat
2. Saat workflow berjalan, method `execute(state)` dipanggil
3. execute() akan:
   - Memanggil build_prompt(state) untuk membuat prompt
   - Mengirim prompt ke LLM
   - Memanggil process_response(state, response) untuk memproses hasil
4. State yang sudah diupdate dikembalikan ke workflow


TIPS:
-----

- Gunakan FILE_FORMAT_INSTRUCTIONS di prompt untuk konsistensi format file output
- Selalu validasi required_fields sebelum build_prompt
- Gunakan state.get(key, "") untuk akses aman ke state
- Agent yang di-skip bisa return state langsung tanpa memanggil LLM

"""

from abc import ABC, abstractmethod
from typing import List, Tuple, Any, Dict, Optional
from langchain_core.messages import HumanMessage

from ..core.llm import llm
from .prompts import FILE_FORMAT_INSTRUCTIONS


class BaseAgent(ABC):
    """
    Base class untuk semua agent dalam SATGAS framework.

    Extend class ini untuk membuat agent baru. Setiap agent harus
    mendefinisikan metadata dan mengimplementasikan method abstrak.

    Attributes:
        agent_id (str): ID unik agent, digunakan sebagai node name di workflow
        agent_name (str): Nama agent untuk logging dan UI
        display_name (str): Nama yang ditampilkan ke LLM dalam prompt
        step_order (int): Urutan eksekusi dalam pipeline (1-based)
        description (str): Deskripsi singkat fungsi agent
        color (str): Warna hex untuk UI
        output_fields (List[Tuple]): List of (field_name, filename, language)
        required_fields (List[str]): Field yang harus ada di state sebelum eksekusi
    """

    # =========================================================================
    # METADATA - Override di subclass
    # =========================================================================

    agent_id: str = ""              # ID unik, contoh: "backend"
    agent_name: str = ""            # Nama untuk logging, contoh: "Backend"
    display_name: str = ""          # Nama untuk LLM, contoh: "Backend Engineer"
    step_order: int = 0             # Urutan eksekusi (1 = pertama)
    description: str = ""           # Deskripsi singkat
    color: str = "#666666"          # Warna UI (hex)

    # Output fields: list of (state_key, filename, language)
    # Contoh: [("backend_code", "backend_code.py", "python")]
    output_fields: List[Tuple[str, str, str]] = []

    # Required fields dari state yang harus ada sebelum agent dijalankan
    required_fields: List[str] = []

    # =========================================================================
    # CONSTRUCTOR
    # =========================================================================

    def __init__(self):
        """Initialize agent. Override jika perlu custom initialization."""
        self._validate_metadata()

    def _validate_metadata(self):
        """Validasi metadata agent sudah diisi dengan benar."""
        if not self.agent_id:
            raise ValueError(f"{self.__class__.__name__}: agent_id harus diisi")
        if not self.agent_name:
            raise ValueError(f"{self.__class__.__name__}: agent_name harus diisi")
        if self.step_order <= 0:
            raise ValueError(f"{self.__class__.__name__}: step_order harus > 0")

    # =========================================================================
    # ABSTRACT METHODS - Harus diimplementasikan di subclass
    # =========================================================================

    @abstractmethod
    def build_prompt(self, state: Dict[str, Any]) -> str:
        """
        Bangun prompt untuk dikirim ke LLM.

        Args:
            state: State dictionary dari workflow

        Returns:
            String prompt yang akan dikirim ke LLM

        Contoh implementasi:
            def build_prompt(self, state):
                spec = state.get("spec", "")
                return f'''
                Kamu adalah {self.display_name}.

                TUGAS: Implementasi backend berdasarkan spesifikasi.

                SPESIFIKASI:
                {spec}

                {FILE_FORMAT_INSTRUCTIONS}
                '''
        """
        pass

    @abstractmethod
    def process_response(self, state: Dict[str, Any], response: Any) -> Dict[str, Any]:
        """
        Proses response dari LLM dan update state.

        Args:
            state: State dictionary dari workflow
            response: Response object dari LLM (memiliki .content)

        Returns:
            State yang sudah diupdate

        Contoh implementasi:
            def process_response(self, state, response):
                state["backend_code"] = response.content
                state["status"] = "backend_done"
                return state
        """
        pass

    # =========================================================================
    # MAIN EXECUTION - Biasanya tidak perlu di-override
    # =========================================================================

    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Eksekusi agent: build prompt -> call LLM -> process response.

        Method ini adalah entry point yang dipanggil oleh workflow.
        Biasanya tidak perlu di-override kecuali butuh custom logic.

        IMPORTANT: For parallel execution support, this method returns ONLY
        the keys that were modified by this agent. This prevents conflicts
        when parallel branches (like backend+frontend) merge their outputs.

        Args:
            state: State dictionary dari workflow

        Returns:
            Dictionary containing ONLY the modified keys
        """
        # Validasi required fields
        self._check_required_fields(state)

        # Set current agent untuk logging
        llm.set_current_agent(self.display_name or self.agent_name)

        # Save original state values to detect changes
        original_state = {k: v for k, v in state.items()}

        # Build prompt
        prompt = self.build_prompt(state)

        # Call LLM
        response = llm.invoke([HumanMessage(content=prompt)])

        # Process response dan update state
        updated_state = self.process_response(state, response)

        # Return ONLY modified keys for parallel execution support
        # This prevents "INVALID_CONCURRENT_GRAPH_UPDATE" errors when
        # parallel branches (backend+frontend, test+security+qa) merge
        modified = {}
        for key, value in updated_state.items():
            if key not in original_state or original_state[key] != value:
                modified[key] = value

        # Always return at least the status if nothing else changed
        if not modified:
            modified["status"] = updated_state.get("status", f"{self.agent_id}_done")

        return modified

    def _check_required_fields(self, state: Dict[str, Any]):
        """
        Validasi bahwa semua required_fields ada di state.

        Raises:
            ValueError: Jika ada required field yang kosong
        """
        for field in self.required_fields:
            if not state.get(field):
                raise ValueError(
                    f"{self.agent_name}: Required field '{field}' kosong di state. "
                    f"Pastikan agent sebelumnya sudah mengisi field ini."
                )

    # =========================================================================
    # HELPER METHODS - Bisa digunakan di subclass
    # =========================================================================

    def get_file_format_instructions(self) -> str:
        """
        Dapatkan instruksi format file untuk prompt.

        Gunakan ini di build_prompt() untuk memastikan LLM menggunakan
        format file yang konsisten (===FILE: path===).

        Returns:
            String instruksi format file
        """
        return FILE_FORMAT_INSTRUCTIONS

    def skip_execution(self, state: Dict[str, Any], reason: str = "") -> Dict[str, Any]:
        """
        Skip eksekusi agent dan return empty dict (no modifications).

        Gunakan ini jika kondisi tertentu terpenuhi dan agent tidak perlu
        dijalankan. Contoh: skip security agent jika tidak ada backend code.

        IMPORTANT: Returns empty dict for parallel execution support.
        This prevents conflicts when skipped agents run in parallel.

        Args:
            state: State dictionary
            reason: Alasan skip (untuk logging)

        Returns:
            Empty dict (no modifications to state)
        """
        if reason:
            llm.set_current_agent(self.display_name or self.agent_name)
            llm._notify_status(f">>> Skipped: {reason}")
        # Return empty dict - no modifications for parallel execution support
        return {}

    # =========================================================================
    # CONVERSION TO CALLABLE - Untuk kompatibilitas dengan LangGraph
    # =========================================================================

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Membuat agent callable sehingga bisa langsung digunakan di LangGraph.

        Ini memungkinkan:
            workflow.add_node("backend", BackendAgent())
        """
        return self.execute(state)

    # =========================================================================
    # UI CONFIG GENERATION
    # =========================================================================

    def to_config(self) -> Dict[str, Any]:
        """
        Generate config dictionary untuk UI.

        Returns:
            Dictionary dengan format yang sesuai untuk AGENTS_CONFIG
        """
        return {
            "id": self.agent_id,
            "name": self.agent_name,
            "step": self.step_order,
            "color": self.color,
            "description": self.description,
            "outputs": self.output_fields,
        }

    # =========================================================================
    # STRING REPRESENTATION
    # =========================================================================

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.agent_id}, step={self.step_order})>"
