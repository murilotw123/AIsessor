"""Google Agenda via Google Calendar API (OAuth). Credenciais ficam em credentials.json/token.json."""
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from . import config
from .agenda_base import Evento

RAIZ = Path(__file__).resolve().parent.parent
CREDENCIAIS = RAIZ / "credentials.json"  # baixado do Google Cloud
TOKEN = RAIZ / "token.json"  # criado por: python -m assessor.google_login
ESCOPOS = ["https://www.googleapis.com/auth/calendar"]

_servico = None


def _api():
    """Cria (uma vez) o cliente da API, renovando o token se preciso."""
    global _servico
    if _servico is None:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        if not TOKEN.exists():
            raise RuntimeError("Google não autorizado. Rode: python -m assessor.google_login")
        cred = Credentials.from_authorized_user_file(str(TOKEN), ESCOPOS)
        if not cred.valid and cred.refresh_token:
            cred.refresh(Request())
            TOKEN.write_text(cred.to_json())
        _servico = build("calendar", "v3", credentials=cred, cache_discovery=False)
    return _servico


def _corpo_horario(dt: datetime) -> dict:
    return {"dateTime": dt.isoformat(), "timeZone": config.TIMEZONE}


def _para_evento(e: dict) -> Evento:
    tz = ZoneInfo(config.TIMEZONE)
    ini, fim = e["start"], e["end"]
    dia_inteiro = "date" in ini
    if dia_inteiro:
        i = datetime.fromisoformat(ini["date"]).replace(tzinfo=tz)
        f = datetime.fromisoformat(fim["date"]).replace(tzinfo=tz)
    else:
        i = datetime.fromisoformat(ini["dateTime"]).astimezone(tz)
        f = datetime.fromisoformat(fim["dateTime"]).astimezone(tz)
    return Evento("google", e["id"], e.get("summary", "(sem título)"), i, f, e.get("location", ""), dia_inteiro)


def listar(inicio: datetime, fim: datetime) -> list[Evento]:
    resp = _api().events().list(
        calendarId="primary", timeMin=inicio.isoformat(), timeMax=fim.isoformat(),
        singleEvents=True, orderBy="startTime", maxResults=100,
    ).execute()
    return [_para_evento(e) for e in resp.get("items", []) if e.get("status") != "cancelled"]


def criar(titulo: str, inicio: datetime, fim: datetime, local: str = "", descricao: str = "",
          meet: bool = False) -> str:
    """Cria o evento e devolve o link do Google Meet ("" se não pediu sala)."""
    corpo = {"summary": titulo, "start": _corpo_horario(inicio), "end": _corpo_horario(fim)}
    if local:
        corpo["location"] = local
    if descricao:
        corpo["description"] = descricao
    if meet:  # pede ao Google para criar a sala do Meet junto com o evento
        corpo["conferenceData"] = {"createRequest": {
            "requestId": uuid.uuid4().hex, "conferenceSolutionKey": {"type": "hangoutsMeet"}}}
    criado = _api().events().insert(calendarId="primary", body=corpo, conferenceDataVersion=1).execute()
    return criado.get("hangoutLink", "")


def editar(id: str, titulo=None, inicio=None, fim=None, local=None) -> None:
    corpo = {}
    if titulo:
        corpo["summary"] = titulo
    if inicio:
        corpo["start"] = _corpo_horario(inicio)
    if fim:
        corpo["end"] = _corpo_horario(fim)
    if local is not None:
        corpo["location"] = local
    _api().events().patch(calendarId="primary", eventId=id, body=corpo).execute()


def cancelar(id: str) -> None:
    _api().events().delete(calendarId="primary", eventId=id).execute()
