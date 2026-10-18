"""Estrutura comum de evento, usada por Google e Apple."""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Evento:
    origem: str  # "google" ou "apple"
    id: str
    titulo: str
    inicio: datetime
    fim: datetime
    local: str = ""
    dia_inteiro: bool = False
