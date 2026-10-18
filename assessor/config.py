"""Configurações lidas do arquivo .env (nunca coloque segredos no código)."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _obrigatoria(nome: str) -> str:
    valor = os.getenv(nome, "").strip()
    if not valor:
        raise SystemExit(f"Variável {nome} não definida no .env (veja o .env.example).")
    return valor


TELEGRAM_BOT_TOKEN = _obrigatoria("TELEGRAM_BOT_TOKEN")
TELEGRAM_USER_ID = int(_obrigatoria("TELEGRAM_USER_ID"))

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
TIMEZONE = os.getenv("TIMEZONE", "America/Sao_Paulo")

# Agendas ativas: "google", "apple" ou "google,apple"
AGENDA = [a.strip().lower() for a in os.getenv("AGENDA", "google").split(",") if a.strip()]
