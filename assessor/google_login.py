"""Autorização única do Google Agenda: python -m assessor.google_login"""
from google_auth_oauthlib.flow import InstalledAppFlow

from .agenda_google import CREDENCIAIS, ESCOPOS, TOKEN

if not CREDENCIAIS.exists():
    raise SystemExit(f"Falta o arquivo {CREDENCIAIS} (baixe do Google Cloud; veja as instruções).")
cred = InstalledAppFlow.from_client_secrets_file(str(CREDENCIAIS), ESCOPOS).run_local_server(port=0)
TOKEN.write_text(cred.to_json())
print("Pronto! Google Agenda autorizado (token.json criado).")
