---
title: Aethelgard SIAT 3D Observatory
emoji: 🇺🇿
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# Aethelgard · SIAT 3D Observatory (Hugging Face Spaces)

[![Hugging Face Spaces](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Spaces-yellow)](https://huggingface.co/spaces)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Three.js](https://img.shields.io/badge/Three.js-0.187%2B-black.svg)](https://threejs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://www.postgresql.org/)
[![Zero Hallucination](https://img.shields.io/badge/Zero_Hallucination-100%25-success.svg)](#)

> **O'zbekiston Respublikasi Prezidenti huzuridagi Statistika agentligi (SIAT / stat.uz)** rasmiy ochiq ma'lumotlari asosida ishlovchi, **100% nol-gallyutsinatsiya (Zero-Hallucination)** kafolati, **11 ta MCP asbobi**, **PostgreSQL gibrid qidiruvi (tsvector + pg_trgm + RRF)** hamda interaktiv **3D xoreografiya** bilan jihozlangan sun'iy intellekt observatoriyasi.

---

## 🚀 Hugging Face Spaces Sozlash va Ishga Tushirish

### 1. Yangi Space yaratish:
1. [Hugging Face Spaces](https://huggingface.co/new-space) sahifasiga kiring.
2. **Space Name:** `aethelgard-siat` (yoki ixtiyoriy nom).
3. **Space SDK:** **Docker** (Blank) ni tanlang.
4. **Space Hardware:** CPU basic (bepul) yoki CPU upgrade.

### 2. Kodni Hugging Face Space-ga Push qilish:
Lokal terminalingizda ushbu `deploy/hf` tarmog'ini Hugging Face masofaviy repozitoriyasiga push qiling:

```bash
# HF repozitoriyangizni remote sifatida qo'shish
git remote add hf https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME

# deploy/hf tarmog'ini Hugging Face main tarmog'iga push qilish
git push hf deploy/hf:main --force
```

*(Eslatma: Agar Hugging Face to'g'ridan-to'g'ri `README.md` ni o'qishi kerak bo'lsa, push qilishdan oldin `README_HF.md` faylini `README.md` sifatida nusxalab qo'yishingiz mumkin: `cp README_HF.md README.md`)*.

---

### 3. API Kalitini Sozlash (Repository Secrets):
1. Hugging Face Space sahifangizda **Settings** bo'limiga o'ting.
2. **Variables and secrets** bo'limiga tushing.
3. **New secret** tugmasini bosing:
   - **Name:** `GEMINI_API_KEY`
   - **Value:** Sizning Google Gemini API kalitingiz.
4. Space avtomatik ravishda qayta yuklanadi va to'liq jonli rejimda ishlay boshlaydi!

---

## 🌐 100% Oflayn Deterministik Demo Rejim

Agar `GEMINI_API_KEY` kiritilmagan bo'lsa ham yoki tarmoq holatini tekshirish uchun tizimda to'liq oflayn kesh rejimi mavjud:

👉 **`https://YOUR_SPACE_NAME.hf.space/?demo`**

Ushbu rejimda barcha 3D o'tishlar, xarita, DWH server rack animatsiyasi va grafiklar internet yoki LLM API so'rovlarisiz bir zumda ishlaydi.

---

## 🏛 Texnik Arxitektura
* **Container:** Multi-stage Docker (Node.js 20 build + Python 3.11-slim runtime).
* **Database:** Embedded PostgreSQL 16 server (localhost:5432) with pre-loaded `siat_dwh` database (3 232 indicators, 2.58M+ facts, trigram and tsvector indexes).
* **Backend:** FastAPI serving REST API, Server-Sent Events (SSE) streaming on port `7860`.
* **Frontend:** Built Three.js + Vite single-page application served directly from FastAPI static mount.
