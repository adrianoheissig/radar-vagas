"""
Interface comum para todas as fontes de vagas.

ABC = Abstract Base Class. Uma classe com @abstractmethod não pode ser
instanciada diretamente; as subclasses são obrigadas a implementar o método.
É o equivalente a uma `interface` do Java/TypeScript.
"""

import logging
import time
from abc import ABC, abstractmethod

import requests

from collector import config
from collector.models import Vaga
from collector.perfil import Perfil
from collector.utils import criar_sessao


class Fonte(ABC):
    # Atributo de classe: cada subclasse define o seu.
    # É o nome usado em config.FONTES_ATIVAS e no campo `fonte` da vaga.
    nome: str = "base"

    def __init__(self, perfil: Perfil | None = None, sessao: requests.Session | None = None) -> None:
        # O perfil diz O QUE buscar (termos, cidades). Sem perfil, usa o padrão do config.py.
        self.perfil = perfil or Perfil.padrao()
        self.sessao = sessao or criar_sessao()
        # Logger com nome da fonte: aparece como "fonte.adzuna" no log.
        self.log = logging.getLogger(f"fonte.{self.nome}")

    def disponivel(self) -> bool:
        """Retorna False quando a fonte não pode rodar (ex.: falta a API key).

        A implementação padrão sempre retorna True; sobrescreva se precisar.
        """
        return True

    @abstractmethod
    def fetch(self) -> list[Vaga]:
        """Busca as vagas na origem e devolve uma lista de Vaga (sem score)."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Auxiliares para as subclasses
    # ------------------------------------------------------------------

    def _get(self, url: str, **kwargs) -> requests.Response:
        """GET com timeout e erro para status HTTP >= 400.

        **kwargs repassa quaisquer argumentos nomeados (params=, headers=...)
        direto para requests.get.
        """
        resposta = self.sessao.get(url, timeout=config.TIMEOUT_HTTP, **kwargs)
        resposta.raise_for_status()
        return resposta

    def _pausa(self) -> None:
        """Espera entre chamadas para não sobrecarregar o servidor."""
        time.sleep(config.PAUSA_ENTRE_CHAMADAS)

    def _criar_vaga(self, **campos) -> Vaga | None:
        """Cria a Vaga tratando dados inválidos (ex.: sem URL) sem derrubar a fonte."""
        try:
            return Vaga(fonte=self.nome, **campos)
        except ValueError as erro:
            self.log.debug("vaga_ignorada motivo=%s", erro)
            return None
