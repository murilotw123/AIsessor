"""Lembretes: salvos no SQLite e enviados automaticamente na hora certa."""
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram.ext import ContextTypes

from . import config, db

log = logging.getLogger(__name__)


def _agora() -> datetime:
    return datetime.now(ZoneInfo(config.TIMEZONE)).replace(tzinfo=None)


def criar_lembrete(texto: str, quando: str) -> str:
    """`quando` em AAAA-MM-DDTHH:MM (horário de Brasília)."""
    dt = datetime.fromisoformat(quando).replace(tzinfo=None, second=0, microsecond=0)
    if dt <= _agora():
        return "Esse horário já passou. Peça outro horário."
    with db.conectar() as con:
        cur = con.execute("INSERT INTO lembretes (texto, quando) VALUES (?,?)", (texto, dt.isoformat(timespec="minutes")))
    return f"Lembrete #{cur.lastrowid} criado para {dt:%d/%m/%Y %H:%M}: {texto}"


def listar_lembretes() -> str:
    with db.conectar() as con:
        linhas = con.execute("SELECT * FROM lembretes WHERE enviado=0 ORDER BY quando").fetchall()
    if not linhas:
        return "Nenhum lembrete pendente."
    return "\n".join(f"#{l['id']} {datetime.fromisoformat(l['quando']):%d/%m %H:%M} — {l['texto']}" for l in linhas)


def cancelar_lembrete(id: int) -> str:
    with db.conectar() as con:
        cur = con.execute("DELETE FROM lembretes WHERE id=? AND enviado=0", (int(id),))
    return f"Lembrete #{id} cancelado." if cur.rowcount else f"Lembrete #{id} não encontrado."


async def enviar_vencidos(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Roda a cada 30s: envia os lembretes cujo horário chegou e marca como enviados."""
    with db.conectar() as con:
        vencidos = con.execute(
            "SELECT * FROM lembretes WHERE enviado=0 AND quando<=?", (_agora().isoformat(timespec="minutes"),)
        ).fetchall()
    for l in vencidos:
        try:
            await context.bot.send_message(config.TELEGRAM_USER_ID, f"⏰ Lembrete: {l['texto']}")
        except Exception:
            log.exception("Falha ao enviar lembrete %s (tentará de novo)", l["id"])
            continue
        with db.conectar() as con:
            con.execute("UPDATE lembretes SET enviado=1 WHERE id=?", (l["id"],))


FERRAMENTAS = [
    {"type": "function", "function": {
        "name": "criar_lembrete",
        "description": "Cria um lembrete que será enviado ao usuário no horário indicado.",
        "parameters": {"type": "object", "properties": {
            "texto": {"type": "string", "description": "O que lembrar, ex: 'ligar pro contador'"},
            "quando": {"type": "string", "description": "AAAA-MM-DDTHH:MM, calculado a partir da data/hora atual"},
        }, "required": ["texto", "quando"]}}},
    {"type": "function", "function": {
        "name": "listar_lembretes", "description": "Lista os lembretes pendentes.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "cancelar_lembrete", "description": "Cancela um lembrete pendente pelo id.",
        "parameters": {"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]}}},
]
EXECUTORES = {f: globals()[f] for f in ("criar_lembrete", "listar_lembretes", "cancelar_lembrete")}
