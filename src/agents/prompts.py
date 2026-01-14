"""Shared prompt templates for agents."""

# =============================================================================
# STRICT OUTPUT RULES - Mencegah LLM menambahkan komentar/penjelasan
# =============================================================================

STRICT_OUTPUT_RULES = """
ATURAN OUTPUT KETAT (SANGAT PENTING - WAJIB DIPATUHI):

1. HANYA OUTPUT FILE - TIDAK ADA YANG LAIN:
   - JANGAN tulis penjelasan, komentar, atau teks apapun di luar file
   - JANGAN tulis "Saya akan...", "Mari kita...", "Berikut adalah...", dll
   - JANGAN tulis "I'll...", "Let me...", "Here's...", dll
   - JANGAN tulis catatan, ringkasan, atau kesimpulan
   - LANGSUNG mulai dengan ===FILE: tanpa pembuka apapun

2. TIDAK ADA KOMENTAR DI ANTARA FILE:
   - Setelah ===END_FILE===, LANGSUNG tulis ===FILE: berikutnya
   - TIDAK ADA baris kosong berlebihan
   - TIDAK ADA penjelasan antara file

3. FORMAT OUTPUT YANG BENAR:
===FILE: path/file1.py===
...kode...
===END_FILE===
===FILE: path/file2.py===
...kode...
===END_FILE===

4. FORMAT OUTPUT YANG SALAH (JANGAN SEPERTI INI):
"Saya akan membuat backend API..."  ← SALAH! Jangan tulis ini
===FILE: path/file1.py===
...kode...
===END_FILE===
"Selanjutnya, mari buat..."  ← SALAH! Jangan tulis ini
===FILE: path/file2.py===
...kode...
===END_FILE===
"Selesai! Berikut adalah ringkasan..."  ← SALAH! Jangan tulis ini

INGAT: Output HANYA boleh berisi ===FILE:=== ... ===END_FILE=== tanpa teks lain!
"""

CODE_STYLE_INSTRUCTIONS = """
CODE FORMATTING RULES (WAJIB DIIKUTI):

KESALAHAN UMUM YANG HARUS DIHINDARI:
- JANGAN masukkan 'sqlite3' di requirements.txt (sqlite3 adalah modul bawaan Python)
- JANGAN masukkan modul bawaan Python lainnya di requirements.txt (os, sys, json, re, dll)
- Hanya masukkan package eksternal yang perlu diinstall via pip

1. INDENTASI:
   - JavaScript/TypeScript/JSON: 2 spasi
   - Python: 4 spasi
   - YAML: 2 spasi
   - HTML/JSX/Vue/Svelte: 2 spasi
   - CSS/SCSS: 2 spasi
   - Go: tab
   - PHP: 4 spasi

2. FORMATTING STYLE (seperti Prettier):
   - Gunakan single quotes untuk JavaScript/TypeScript (kecuali JSX attributes)
   - Gunakan double quotes untuk JSON
   - Tambahkan trailing comma di multi-line arrays/objects
   - Maksimal 100 karakter per baris, wrap jika lebih panjang
   - Satu baris kosong antara function/class definitions
   - Tidak ada trailing whitespace
   - File harus diakhiri dengan newline

3. STRUKTUR KODE:
   - Import statements di bagian atas, dikelompokkan (external, internal, relative)
   - Satu baris kosong setelah imports
   - Constants sebelum functions
   - Export statements di bagian bawah (jika applicable)

4. CONTOH FORMATTING YANG BENAR:

JavaScript/React (2 spasi):
```javascript
import React, { useState, useEffect } from 'react';
import axios from 'axios';

import { Button } from './components/Button';

const API_URL = '/api/v1';

const App = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_URL}/items`);
      setData(response.data);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      {loading ? (
        <p>Loading...</p>
      ) : (
        <ul>
          {data.map((item) => (
            <li key={item.id}>{item.name}</li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default App;
```

Python/FastAPI (4 spasi):
```python
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel

from .database import get_db
from .models import Item


app = FastAPI()


class ItemCreate(BaseModel):
    name: str
    price: float
    description: Optional[str] = None


class ItemResponse(BaseModel):
    id: int
    name: str
    price: float

    class Config:
        from_attributes = True


@app.get("/items", response_model=List[ItemResponse])
async def get_items(db=Depends(get_db)):
    items = db.query(Item).all()
    return items


@app.post("/items", response_model=ItemResponse)
async def create_item(item: ItemCreate, db=Depends(get_db)):
    db_item = Item(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item
```
"""

FILE_FORMAT_INSTRUCTIONS = f"""
{STRICT_OUTPUT_RULES}

FORMAT OUTPUT WAJIB - Output setiap file dengan format berikut:
===FILE: path/to/file.ext===
isi file disini
===END_FILE===

SANGAT PENTING - INDENTASI PYTHON:
Untuk Python, WAJIB gunakan 4 spasi untuk setiap level indentasi.
Kode Python TANPA indentasi akan ERROR dan tidak bisa dijalankan!

CONTOH YANG BENAR (perhatikan 4 spasi indentasi):
===FILE: backend/app/main.py===
from fastapi import FastAPI

app = FastAPI(title="My API")


@app.get("/")
def read_root():
    return {{"message": "Hello World"}}


@app.get("/items/{{item_id}}")
def get_item(item_id: int):
    if item_id < 0:
        return {{"error": "Invalid ID"}}
    return {{"item_id": item_id}}
===END_FILE===

CONTOH CLASS DENGAN INDENTASI:
===FILE: backend/app/models.py===
from sqlalchemy import Column, Integer, String
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    email = Column(String(200))

    def __repr__(self):
        return f"<User(name={{self.name}})>"
===END_FILE===

PERINGATAN KERAS:
- Setiap function body HARUS di-indent 4 spasi
- Setiap class body HARUS di-indent 4 spasi
- Setiap if/for/while body HARUS di-indent 4 spasi
- JANGAN PERNAH tulis kode Python tanpa indentasi!

{CODE_STYLE_INSTRUCTIONS}
"""
