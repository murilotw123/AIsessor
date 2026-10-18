"""Agenda: ferramentas da IA + confirmação obrigatória antes de criar/editar/cancelar.

Criar, editar e cancelar NÃO executam na hora: guardam uma ação pendente e mostram os
detalhes. Só quando o usuário diz "sim" (tratado no bot, em código) a ação é executada.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from . import agenda_google, config

DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
SIM = {"sim", "s", "confirma", "confirmo", "confirmado", "pode", "ok", "isso", "positivo", "claro"}
NAO = {"não", "nao", "n", "cancela", "deixa", "negativo"}

LOCAIS_ONLINE = {"online", "meet", "google meet", "virtual", "remoto", "videochamada"}

pendente: dict | None = None  # {"descricao": str, "executar": callable}
_ultimos: dict[int, "Evento"] = {}  # número mostrado na listagem -> evento


def _provedores() -> list:
    """Agendas ativas, conforme AGENDA no .env (google, apple ou google,apple)."""
    mods = []
    for nome in config.AGENDA:
        if nome == "google":
            mods.append(agenda_google)
        elif nome == "apple":
            from . import agenda_apple  # entra na última etapa
            mods.append(agenda_apple)
    return mods


def _dt(texto: str) -> datetime:
    return datetime.fromisoformat(texto).replace(tzinfo=ZoneInfo(config.TIMEZONE))


def _fmt(e) -> str:
    if e.dia_inteiro:
        return f"{DIAS[e.inicio.weekday()]} {e.inicio:%d/%m} (dia todo) — {e.titulo}"
    local = f" @ {e.local}" if e.local else ""
    return f"{DIAS[e.inicio.weekday()]} {e.inicio:%d/%m} {e.inicio:%H:%M}–{e.fim:%H:%M} — {e.titulo}{local}"


def listar_eventos(data_inicio: str, data_fim: str = "") -> str:
    """Eventos de data_inicio até data_fim (inclusive), ambos AAAA-MM-DD."""
    ini = _dt(data_inicio[:10] + "T00:00")
    fim = _dt((data_fim or data_inicio)[:10] + "T00:00") + timedelta(days=1)
    eventos = []
    for p in _provedores():
        eventos += p.listar(ini, fim)
    eventos.sort(key=lambda e: e.inicio)
    _ultimos.clear()
    if not eventos:
        return "Nenhum compromisso nesse período. 🎉"
    linhas = []
    for n, e in enumerate(eventos, 1):
        _ultimos[n] = e
        linhas.append(f"{n}. {_fmt(e)}")
    return "📅 Seus compromissos:\n" + "\n".join(linhas)


def _propor(descricao: str, executar) -> str:
    global pendente
    pendente = {"descricao": descricao, "executar": executar}
    return f"{descricao}\n\nConfirma? (responda sim ou não)"


def criar_evento(titulo: str, inicio: str, fim: str = "", local: str = "") -> str:
    """Propõe criar um evento (inicio/fim em AAAA-MM-DDTHH:MM). Sem fim = 1 hora."""
    i = _dt(inicio)
    f = _dt(fim) if fim else i + timedelta(hours=1)
    prov = _provedores()[0]  # novos eventos vão para a primeira agenda configurada

    # Sala do Meet automática, exceto quando o local é físico (só vale para o Google).
    meet = prov is agenda_google and (not local or local.strip().lower() in LOCAIS_ONLINE)

    def executar():
        link = prov.criar(titulo, i, f, local, meet=meet) if prov is agenda_google else prov.criar(titulo, i, f, local)
        msg = f"✅ Evento criado: {titulo}, {i:%d/%m} das {i:%H:%M} às {f:%H:%M}."
        return msg + (f"\n🎥 Google Meet: {link}" if link else "")

    quando = f"{DIAS[i.weekday()]} {i:%d/%m} das {i:%H:%M} às {f:%H:%M}"
    return _propor(f"📝 Criar evento: {titulo}\n🕒 {quando}" + (f"\n📍 {local}" if local else "")
                   + ("\n🎥 Com sala do Google Meet" if meet else ""), executar)


def _achar(numero: int):
    e = _ultimos.get(int(numero))
    if e is None:
        raise ValueError("Número inválido. Liste os compromissos primeiro (listar_eventos).")
    return e


def _prov_de(e):
    return next(p for p in _provedores() if p.__name__.endswith(e.origem))


def editar_evento(numero: int, titulo: str = "", inicio: str = "", fim: str = "", local: str = "") -> str:
    """Propõe editar o evento de número `numero` da última listagem."""
    e = _achar(numero)
    novo_i = _dt(inicio) if inicio else None
    # Mudou só o início? Mantém a duração original.
    novo_f = _dt(fim) if fim else (novo_i + (e.fim - e.inicio) if novo_i else None)

    def executar():
        _prov_de(e).editar(e.id, titulo or None, novo_i, novo_f, local or None)
        return f"✅ Evento atualizado: {titulo or e.titulo}."

    mudancas = []
    if titulo:
        mudancas.append(f"título → {titulo}")
    if novo_i:
        mudancas.append(f"horário → {novo_i:%d/%m %H:%M}–{novo_f:%H:%M}")
    if local:
        mudancas.append(f"local → {local}")
    return _propor(f"✏️ Editar: {_fmt(e)}\n" + "\n".join(mudancas), executar)


def cancelar_evento(numero: int) -> str:
    """Propõe cancelar o evento de número `numero` da última listagem."""
    e = _achar(numero)

    def executar():
        _prov_de(e).cancelar(e.id)
        return f"🗑️ Evento cancelado: {e.titulo}."

    return _propor(f"🗑️ Cancelar: {_fmt(e)}", executar)


def resposta_pendente(texto: str) -> str | None:
    """Se há ação pendente e o usuário respondeu sim/não, trata e devolve a resposta; senão None."""
    global pendente
    if pendente is None:
        return None
    palavras = texto.lower().replace(",", " ").replace(".", " ").replace("!", " ").split()
    if not palavras:
        return None
    if palavras[0] in NAO or "não" in palavras or "nao" in palavras:
        pendente = None
        return "Certo, não fiz nada."
    if palavras[0] in SIM:
        acao, pendente = pendente, None
        try:
            return acao["executar"]()
        except Exception as erro:
            return f"Não consegui concluir: {erro}"
    return None  # outra coisa: segue a conversa normal (a pendência continua)


FERRAMENTAS = [
    {"type": "function", "function": {
        "name": "listar_eventos",
        "description": "Lista compromissos da agenda num período. 'amanhã' = data de amanhã nos dois campos; "
                       "'minha semana' = de hoje até domingo.",
        "parameters": {"type": "object", "properties": {
            "data_inicio": {"type": "string", "description": "AAAA-MM-DD"},
            "data_fim": {"type": "string", "description": "AAAA-MM-DD (inclusive); omita para um dia só"},
        }, "required": ["data_inicio"]}}},
    {"type": "function", "function": {
        "name": "criar_evento",
        "description": "Cria um evento na agenda (o usuário ainda vai confirmar). Calcule a data a partir de hoje.",
        "parameters": {"type": "object", "properties": {
            "titulo": {"type": "string"},
            "inicio": {"type": "string", "description": "AAAA-MM-DDTHH:MM"},
            "fim": {"type": "string", "description": "AAAA-MM-DDTHH:MM; omita se não informado"},
            "local": {"type": "string"},
        }, "required": ["titulo", "inicio"]}}},
    {"type": "function", "function": {
        "name": "editar_evento",
        "description": "Edita um evento usando o NÚMERO da última listagem. Se não houver listagem recente, "
                       "chame listar_eventos antes.",
        "parameters": {"type": "object", "properties": {
            "numero": {"type": "integer"}, "titulo": {"type": "string"},
            "inicio": {"type": "string", "description": "AAAA-MM-DDTHH:MM"},
            "fim": {"type": "string", "description": "AAAA-MM-DDTHH:MM"}, "local": {"type": "string"},
        }, "required": ["numero"]}}},
    {"type": "function", "function": {
        "name": "cancelar_evento",
        "description": "Cancela um evento pelo NÚMERO da última listagem (chame listar_eventos antes se preciso).",
        "parameters": {"type": "object", "properties": {"numero": {"type": "integer"}}, "required": ["numero"]}}},
]
EXECUTORES = {f: globals()[f] for f in ("listar_eventos", "criar_evento", "editar_evento", "cancelar_evento")}
