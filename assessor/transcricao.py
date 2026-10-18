"""Transcrição de áudio para texto, 100% local, com faster-whisper."""
from pathlib import Path

from . import config

_modelo = None


def _carregar_modelo():
    """Carrega o modelo só na primeira vez (o download inicial pode demorar)."""
    global _modelo
    if _modelo is None:
        from faster_whisper import WhisperModel

        _modelo = WhisperModel(config.WHISPER_MODEL, device="cpu", compute_type="int8")
    return _modelo


def transcrever(caminho: Path) -> str:
    """Transcreve um arquivo de áudio em português. Função bloqueante."""
    segmentos, _ = _carregar_modelo().transcribe(str(caminho), language="pt", vad_filter=True)
    return " ".join(s.text.strip() for s in segmentos).strip()
