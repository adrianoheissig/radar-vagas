"""
Registro das fontes de vagas.

Para adicionar uma fonte nova:
  1. Crie collector/sources/minha_fonte.py com uma classe que herda de Fonte
     e implementa fetch() -> list[Vaga].
  2. Importe-a aqui e adicione na lista TODAS_AS_FONTES.
  3. Adicione "minha_fonte": True em config.FONTES_ATIVAS.

A ordem da lista é a ordem de prioridade (e de execução).
"""

from collector.sources.adzuna import AdzunaFonte
from collector.sources.base import Fonte
from collector.sources.gupy import GupyFonte
from collector.sources.infojobs import InfoJobsFonte
from collector.sources.jsearch import JSearchFonte

TODAS_AS_FONTES: list[type[Fonte]] = [
    AdzunaFonte,
    JSearchFonte,
    GupyFonte,
    InfoJobsFonte,
]

# __all__ define o que `from collector.sources import *` exporta.
__all__ = ["Fonte", "TODAS_AS_FONTES"]
