"""Gastos: salvar, corrigir, apagar e gerar relatório mensal."""
from datetime import date, datetime
from zoneinfo import ZoneInfo

from . import config, db


def _hoje() -> date:
    return datetime.now(ZoneInfo(config.TIMEZONE)).date()


def _brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def salvar_gasto(valor: float, descricao: str, categoria: str, data: str = "") -> str:
    """Salva um gasto. `data` em AAAA-MM-DD; vazio = hoje."""
    d = date.fromisoformat(data) if data else _hoje()
    with db.conectar() as con:
        cur = con.execute(
            "INSERT INTO gastos (valor, descricao, categoria, data) VALUES (?,?,?,?)",
            (float(valor), descricao, categoria.lower(), d.isoformat()),
        )
    return f"Gasto #{cur.lastrowid} salvo: {_brl(float(valor))} em {descricao} ({categoria.lower()}) em {d:%d/%m/%Y}."


def corrigir_gasto(id: int, valor: float = None, descricao: str = None,
                   categoria: str = None, data: str = None) -> str:
    """Altera só os campos informados de um gasto existente."""
    campos = {"valor": valor, "descricao": descricao,
              "categoria": categoria.lower() if categoria else None, "data": data or None}
    campos = {k: v for k, v in campos.items() if v is not None}
    if not campos:
        return "Nada para alterar."
    if "data" in campos:
        date.fromisoformat(campos["data"])  # valida o formato
    with db.conectar() as con:
        cur = con.execute(
            f"UPDATE gastos SET {', '.join(k + '=?' for k in campos)} WHERE id=?",
            (*campos.values(), int(id)),
        )
    return f"Gasto #{id} atualizado." if cur.rowcount else f"Gasto #{id} não encontrado."


def apagar_gasto(id: int) -> str:
    with db.conectar() as con:
        cur = con.execute("DELETE FROM gastos WHERE id=?", (int(id),))
    return f"Gasto #{id} apagado." if cur.rowcount else f"Gasto #{id} não encontrado."


def relatorio_mensal(mes: int = 0, ano: int = 0) -> str:
    """Relatório do mês: total geral, total por categoria e lista. Vazio = mês atual."""
    hoje = _hoje()
    mes, ano = int(mes) or hoje.month, int(ano) or hoje.year
    prefixo = f"{ano:04d}-{mes:02d}"
    with db.conectar() as con:
        linhas = con.execute(
            "SELECT * FROM gastos WHERE data LIKE ? ORDER BY data, id", (prefixo + "-%",)
        ).fetchall()
    if not linhas:
        return f"Nenhum gasto registrado em {mes:02d}/{ano}."

    por_cat: dict[str, float] = {}
    for g in linhas:
        por_cat[g["categoria"]] = por_cat.get(g["categoria"], 0) + g["valor"]
    out = [f"📊 Gastos de {mes:02d}/{ano}", f"Total geral: {_brl(sum(g['valor'] for g in linhas))}", "", "Por categoria:"]
    out += [f"• {c}: {_brl(v)}" for c, v in sorted(por_cat.items(), key=lambda x: -x[1])]
    out += ["", "Lista:"]
    out += [f"#{g['id']} {g['data'][8:]}/{g['data'][5:7]} — {g['descricao']} ({g['categoria']}): {_brl(g['valor'])}" for g in linhas]
    return "\n".join(out)


# Esquemas para a IA
FERRAMENTAS = [
    {"type": "function", "function": {
        "name": "salvar_gasto",
        "description": "Salva um gasto do usuário. Deduza valor, descrição, categoria e data da frase.",
        "parameters": {"type": "object", "properties": {
            "valor": {"type": "number", "description": "Valor em reais"},
            "descricao": {"type": "string"},
            "categoria": {"type": "string", "description": "alimentação, transporte, contas, lazer, saúde, moradia, compras, outros"},
            "data": {"type": "string", "description": "AAAA-MM-DD; omita se for hoje"},
        }, "required": ["valor", "descricao", "categoria"]}}},
    {"type": "function", "function": {
        "name": "corrigir_gasto",
        "description": "Corrige campos de um gasto salvo, pelo id (mostrado no relatório ou ao salvar).",
        "parameters": {"type": "object", "properties": {
            "id": {"type": "integer"}, "valor": {"type": "number"}, "descricao": {"type": "string"},
            "categoria": {"type": "string"}, "data": {"type": "string", "description": "AAAA-MM-DD"},
        }, "required": ["id"]}}},
    {"type": "function", "function": {
        "name": "apagar_gasto",
        "description": "Apaga um gasto pelo id.",
        "parameters": {"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]}}},
    {"type": "function", "function": {
        "name": "relatorio_mensal",
        "description": "Relatório de gastos de um mês (total, por categoria e lista). Repasse o texto ao usuário sem alterar.",
        "parameters": {"type": "object", "properties": {
            "mes": {"type": "integer", "description": "1-12; omita para o mês atual"},
            "ano": {"type": "integer", "description": "omita para o ano atual"},
        }}}},
]
EXECUTORES = {f: globals()[f] for f in ("salvar_gasto", "corrigir_gasto", "apagar_gasto", "relatorio_mensal")}
