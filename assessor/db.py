"""Banco SQLite local (gastos e lembretes)."""
import sqlite3
from pathlib import Path

CAMINHO = Path(__file__).resolve().parent.parent / "assessor.db"


def conectar() -> sqlite3.Connection:
    """Abre uma conexão nova (uma por operação, segura para uso em threads)."""
    con = sqlite3.connect(CAMINHO)
    con.row_factory = sqlite3.Row
    return con


def iniciar() -> None:
    """Cria as tabelas se ainda não existirem."""
    with conectar() as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS gastos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                valor REAL NOT NULL,
                descricao TEXT NOT NULL,
                categoria TEXT NOT NULL,
                data TEXT NOT NULL            -- AAAA-MM-DD
            );
            CREATE TABLE IF NOT EXISTS lembretes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                texto TEXT NOT NULL,
                quando TEXT NOT NULL,         -- AAAA-MM-DDTHH:MM no fuso configurado
                enviado INTEGER NOT NULL DEFAULT 0
            );
            """
        )
