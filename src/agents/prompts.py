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
- DOCKERFILE: Semua komentar HARUS diawali dengan '# ' (hash + spasi), contoh: '# Set environment'

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

# =============================================================================
# PYTHON/FASTAPI SPECIFIC RULES - Mencegah error umum
# =============================================================================

PYTHON_FASTAPI_RULES = """
ATURAN KHUSUS PYTHON/FASTAPI (SANGAT PENTING - WAJIB DIPATUHI):

###############################################################################
# KESALAHAN FATAL YANG HARUS DIHINDARI:
###############################################################################

1. IMPORT LENGKAP UNTUK SQLALCHEMY MODELS:
   SALAH (akan error):
   ```python
   from sqlalchemy import Column, Integer, String
   from app.database import Base

   class User(Base):
       recipes = relationship("Recipe")  # ERROR: relationship not imported!
   ```

   BENAR:
   ```python
   from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
   from sqlalchemy.orm import relationship  # WAJIB import ini jika pakai relationship!
   from sqlalchemy.sql import func
   from app.database import Base

   class User(Base):
       __tablename__ = "users"
       id = Column(Integer, primary_key=True, index=True)
       recipes = relationship("Recipe", back_populates="user")
   ```

2. PYDANTIC V2 CONFIG - HARUS DI DALAM CLASS:
   SALAH (Config tidak akan bekerja):
   ```python
   class UserResponse(BaseModel):
       id: int
       name: str

   class Config:  # SALAH! Config di luar class
       from_attributes = True
   ```

   BENAR:
   ```python
   class UserResponse(BaseModel):
       id: int
       name: str

       class Config:  # BENAR! Config di dalam class dengan indentasi
           from_attributes = True
   ```

3. PYDANTIC-SETTINGS V2 CONFIG:
   SALAH:
   ```python
   class Settings(BaseSettings):
       DATABASE_URL: str

   class Config:  # SALAH! Config di luar
       env_file = ".env"

   settings = Settings()
   ```

   BENAR:
   ```python
   class Settings(BaseSettings):
       DATABASE_URL: str
       SECRET_KEY: str = "default-secret-key"  # Berikan default untuk development

       model_config = SettingsConfigDict(env_file=".env")  # Pydantic v2 style

   settings = Settings()
   ```

4. TRY-EXCEPT INDENTATION:
   SALAH (IndentationError):
   ```python
   try:
       payload = jwt.decode(token, SECRET_KEY)
   username = payload.get("sub")  # SALAH! Harus di dalam try
   except JWTError:  # SALAH! except harus sejajar dengan try
       raise error
   ```

   BENAR:
   ```python
   try:
       payload = jwt.decode(token, SECRET_KEY)
       username = payload.get("sub")  # Di dalam try block
   except JWTError:  # Sejajar dengan try
       raise credentials_exception
   ```

5. IMPORT DARI MODULE YANG BENAR:
   SALAH:
   ```python
   # Di auth.py endpoint
   from app.schemas.auth import Token, TokenData, UserCreate, UserResponse
   # ERROR jika UserCreate, UserResponse tidak ada di schemas/auth.py
   ```

   BENAR:
   ```python
   # Di auth.py endpoint
   from app.schemas.auth import Token, TokenData
   from app.schemas.user import UserCreate, UserResponse  # Import dari module yang benar
   ```

###############################################################################
# TEMPLATE KODE YANG BENAR:
###############################################################################

TEMPLATE MODEL SQLALCHEMY (dengan relationship):
```python
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), nullable=False, unique=True)
    email = Column(String(200), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships - WAJIB import relationship dari sqlalchemy.orm
    recipes = relationship("Recipe", back_populates="user")
    reviews = relationship("Review", back_populates="user")
```

TEMPLATE SCHEMA PYDANTIC V2:
```python
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class UserBase(BaseModel):
    username: str
    email: str


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:  # HARUS di dalam class dengan indentasi 4 spasi
        from_attributes = True
```

TEMPLATE CONFIG PYDANTIC-SETTINGS V2:
```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    PROJECT_NAME: str = "My API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Database - berikan default untuk development
    DATABASE_URL: str = "postgresql://user:pass@localhost/db"

    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )


settings = Settings()
```

TEMPLATE AUTH ENDPOINT (dengan indentasi benar):
```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from typing import Optional

from app import models
from app.database import get_db
from app.core.config import settings
from app.schemas.auth import Token, TokenData
from app.schemas.user import UserCreate, UserResponse  # Import dari module yang benar

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.username == token_data.username).first()
    if user is None:
        raise credentials_exception
    return user


@router.post("/register", response_model=UserResponse)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(
        (models.User.username == user.username) | (models.User.email == user.email)
    ).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already registered")

    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        password_hash=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.post("/login", response_model=Token)
def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
```

CHECKLIST SEBELUM GENERATE KODE:
[x] Semua model yang pakai relationship sudah import `from sqlalchemy.orm import relationship`
[x] Semua schema Response punya `class Config` DI DALAM class
[x] Settings menggunakan `model_config = SettingsConfigDict(...)` untuk Pydantic v2
[x] Semua try-except block memiliki indentasi yang benar
[x] Semua import merujuk ke module yang benar
[x] Semua function/method body memiliki indentasi 4 spasi
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
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    email = Column(String(200))

    recipes = relationship("Recipe", back_populates="user")

    def __repr__(self):
        return f"<User(name={{self.name}})>"
===END_FILE===

PERINGATAN KERAS:
- Setiap function body HARUS di-indent 4 spasi
- Setiap class body HARUS di-indent 4 spasi
- Setiap if/for/while body HARUS di-indent 4 spasi
- JANGAN PERNAH tulis kode Python tanpa indentasi!

{CODE_STYLE_INSTRUCTIONS}

{PYTHON_FASTAPI_RULES}
"""
