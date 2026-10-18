"""Bot do Telegram: recebe texto e áudio, conversa com a IA local (Ollama)."""
import asyncio
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ollama import AsyncClient
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from . import agenda, config, db, ferramentas, lembretes, transcricao

log = logging.getLogger(__name__)

MAX_HISTORICO = 20  # mensagens recentes mantidas como contexto
MAX_RODADAS_TOOLS = 6  # trava de segurança contra loops de ferramentas

cliente = AsyncClient(host=config.OLLAMA_HOST)
historico: list[dict] = []


def prompt_sistema() -> str:
    """Personalidade do assessor, com data e hora atuais para ele se situar."""
    agora = datetime.now(ZoneInfo(config.TIMEZONE))
    return (
        "Você é o assessor pessoal do usuário, dentro do Telegram. "
        "Seja educado, direto e proativo. Responda sempre em português do Brasil, "
        "de forma curta e objetiva. Se faltar uma informação essencial para um pedido, "
        "pergunte. Nunca invente dados.\n"
        "REGRAS IMPORTANTES:\n"
        "- Para qualquer ação (gasto, relatório, lembrete, agenda) CHAME a ferramenta correspondente "
        "imediatamente. Nunca diga 'vou consultar' ou 'aguarde' sem chamar a ferramenta, e nunca "
        "escreva relatórios ou listas de cabeça.\n"
        "- Gasto: descricao = o que foi comprado, curto (ex: 'combustível', 'almoço'); nunca repita "
        "a frase do usuário. Categorias: alimentação (comida, mercado, restaurante), transporte "
        "(posto, combustível, uber, ônibus), contas (luz, água, internet, aluguel), lazer, saúde, "
        "compras, outros.\n"
        "- Eventos: para editar/cancelar, primeiro chame listar_eventos e depois use o número. Para criar/editar/cancelar, apenas chame a ferramenta; a confirmação é feita automaticamente.\n- 'Gastos de hoje/do mês/até agora' = chame relatorio_mensal (mês atual).\n"
        f"Agora: {agora:%A, %d/%m/%Y %H:%M} (fuso {config.TIMEZONE})."
    )


async def responder(texto: str) -> str:
    """Envia o texto à IA, executa as ferramentas que ela pedir e devolve a resposta final."""
    # Confirmação de agenda ("sim"/"não") é tratada aqui, em código, sem passar pela IA.
    confirmacao = await asyncio.to_thread(agenda.resposta_pendente, texto)
    if confirmacao is not None:
        return confirmacao

    mensagens = [{"role": "system", "content": prompt_sistema()}, *historico]
    mensagens.append({"role": "user", "content": texto})

    resposta = ""
    direta = None  # resultado de ferramenta enviado ao usuário exatamente como veio
    for _ in range(MAX_RODADAS_TOOLS):
        args = {"model": config.OLLAMA_MODEL, "messages": mensagens,
                "options": {"temperature": 0.2, "num_ctx": 8192}}
        if ferramentas.FERRAMENTAS:
            args["tools"] = ferramentas.FERRAMENTAS
        retorno = await cliente.chat(**args)
        msg = retorno.message
        mensagens.append(msg)

        if not msg.tool_calls:
            resposta = msg.content or ""
            break
        for chamada in msg.tool_calls:
            resultado = await asyncio.to_thread(
                ferramentas.executar, chamada.function.name, dict(chamada.function.arguments)
            )
            mensagens.append({"role": "tool", "tool_name": chamada.function.name, "content": resultado})
            if chamada.function.name in ferramentas.RESPOSTA_DIRETA:
                direta = resultado
        if direta:
            resposta = direta
            break
    else:
        resposta = "Não consegui concluir esse pedido. Pode tentar de outro jeito?"

    # Guarda só o texto da conversa (sem as chamadas internas de ferramentas).
    historico.extend([{"role": "user", "content": texto}, {"role": "assistant", "content": resposta}])
    del historico[:-MAX_HISTORICO]
    return resposta or "Ok."


async def tratar_texto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.chat.send_action(ChatAction.TYPING)
    await update.message.reply_text(await responder(update.message.text))


async def tratar_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Baixa o áudio, transcreve localmente e trata o texto como mensagem normal."""
    msg = update.message
    await msg.chat.send_action(ChatAction.TYPING)
    arquivo_tg = await (msg.voice or msg.audio).get_file()

    with tempfile.TemporaryDirectory() as pasta:
        caminho = Path(pasta) / "audio"
        await arquivo_tg.download_to_drive(caminho)
        texto = await asyncio.to_thread(transcricao.transcrever, caminho)

    if not texto:
        await msg.reply_text("Não consegui entender o áudio. Pode repetir?")
        return
    await msg.reply_text(f"🎤 Entendi: “{texto}”")
    await msg.chat.send_action(ChatAction.TYPING)
    await msg.reply_text(await responder(texto))


def criar_aplicacao() -> Application:
    db.iniciar()
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    # Só o seu usuário passa pelo filtro; mensagens de outras pessoas são ignoradas.
    so_eu = filters.User(user_id=config.TELEGRAM_USER_ID)
    app.add_handler(MessageHandler(so_eu & filters.TEXT & ~filters.COMMAND, tratar_texto))
    app.add_handler(MessageHandler(so_eu & (filters.VOICE | filters.AUDIO), tratar_audio))
    # Verifica lembretes vencidos a cada 30 segundos.
    app.job_queue.run_repeating(lembretes.enviar_vencidos, interval=30, first=5)
    return app
