"""Registro das ferramentas (tools) que a IA pode chamar.

Gastos e lembretes já registrados; a agenda entra nas próximas etapas.
Cada ferramenta tem um esquema (para a IA) e uma função Python (que executa).
"""
from typing import Any, Callable

from . import agenda, gastos, lembretes

# Esquemas no formato de tool calling do Ollama/OpenAI.
FERRAMENTAS: list[dict] = [*gastos.FERRAMENTAS, *lembretes.FERRAMENTAS, *agenda.FERRAMENTAS]

# Nome da ferramenta -> função que a executa e devolve um texto/dict de resultado.
EXECUTORES: dict[str, Callable[..., Any]] = {**gastos.EXECUTORES, **lembretes.EXECUTORES, **agenda.EXECUTORES}


def executar(nome: str, argumentos: dict) -> str:
    """Executa uma ferramenta pedida pela IA e devolve o resultado como texto."""
    funcao = EXECUTORES.get(nome)
    if funcao is None:
        return f"Erro: ferramenta '{nome}' não existe."
    try:
        return str(funcao(**argumentos))
    except Exception as erro:  # a IA recebe o erro e pode se corrigir
        return f"Erro ao executar '{nome}': {erro}"


# Ferramentas cujo resultado já é a resposta final (evita o modelo reescrever/inventar).
RESPOSTA_DIRETA = {"relatorio_mensal", "listar_lembretes", "listar_eventos",
                    "criar_evento", "editar_evento", "cancelar_evento"}
