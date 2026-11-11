"""
=============================================================================
SIAT STAT DWH: FastAPI Main Application (api/main.py)
Loyiha: siat.stat.uz MCP Loyihasi
Muallif: Siddiq (Backend & Database Lead)
Tavsif:
  FastAPI serveri, CORS sozlamalari va marshrutlar integratsiyasi.
  Port: 8000 | Frontend integratsiyasi: http://localhost:5173 (Vite + 3D)
=============================================================================
"""

import sys
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Loyiha ildizini import yo'liga qo'shish
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.routes import router

app = FastAPI(
    title="SIAT STAT UZ - DWH & Agent API",
    description="O'zbekiston Davlat statistika qo'mitasi (SIAT) ma'lumotlari uchun SSE va REST API infratuzilmasi",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# -----------------------------------------------------------------------------
# CORS Sozlamalari (Vite frontend va barcha mijozlar uchun)
# -----------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Marshrutlarni ulash
app.include_router(router)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"FastAPI serveri http://localhost:{port} da ishga tushirilmoqda...")
    uvicorn.run("api.main:app", host="0.0.0.0", port=port, reload=False)
