"""
Fonte: Adzuna — API oficial e gratuita.

Documentação: https://developer.adzuna.com/docs/search
Endpoint:     GET https://api.adzuna.com/v1/api/jobs/br/search/{pagina}

Cota do plano gratuito (padrão): ~250 chamadas/dia e ~1000/semana.
Esta fonte faz termos_busca x (cidades do perfil + 1) chamadas por
execução = 5 x 3 = 15. Com 3 execuções/dia: 45/dia, 315/semana.
"""

import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from collector.models import Vaga
from collector.sources.base import Fonte
from collector.utils import detectar_modalidade, limpar_html, para_iso_utc

URL_BUSCA = "https://api.adzuna.com/v1/api/jobs/br/search/1"


def limpar_url(url: str) -> str:
    """Remove o parâmetro `se` (id da sessão de busca) da URL da Adzuna.

    Ele muda a cada chamada à API; sem removê-lo, a mesma vaga teria uma URL
    diferente a cada execução e o vagas.json seria regravado à toa.
    """
    partes = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(partes.query) if k != "se"]
    # _replace cria uma cópia da tupla nomeada trocando só o campo indicado.
    return urlunsplit(partes._replace(query=urlencode(query)))


class AdzunaFonte(Fonte):
    nome = "adzuna"

    def __init__(self, *args, **kwargs) -> None:
        # super() chama o __init__ da classe mãe (Fonte).
        super().__init__(*args, **kwargs)
        self.app_id = os.environ.get("ADZUNA_APP_ID", "").strip()
        self.app_key = os.environ.get("ADZUNA_APP_KEY", "").strip()

    def disponivel(self) -> bool:
        if not (self.app_id and self.app_key):
            self.log.warning("fonte_pulada motivo=ADZUNA_APP_ID/ADZUNA_APP_KEY ausentes")
            return False
        return True

    def _consultas(self) -> list[dict]:
        """Monta a lista de combinações termo x cidade, a partir do perfil.

        Para vagas remotas não filtramos local e acrescentamos "remoto" ao termo.
        """
        consultas = []
        for termo in self.perfil.termos_busca:
            for local in self.perfil.localidades_busca():
                consultas.append({"what": termo, "where": local})
            if self.perfil.aceita_remoto:
                consultas.append({"what": f"{termo} remoto"})
        return consultas

    def fetch(self) -> list[Vaga]:
        vagas: list[Vaga] = []
        for consulta in self._consultas():
            params = {
                "app_id": self.app_id,
                "app_key": self.app_key,
                "results_per_page": 50,
                "max_days_old": 30,
                "sort_by": "date",
                "content-type": "application/json",
                **consulta,  # "desempacota" o dict da consulta aqui dentro
            }
            try:
                dados = self._get(URL_BUSCA, params=params).json()
            except Exception as erro:  # noqa: BLE001 - uma consulta ruim não para as outras
                # Cuidado para não logar `params`: ele contém a app_key!
                self.log.warning("consulta_falhou consulta=%s erro=%s",
                                 consulta, type(erro).__name__)
                continue
            finally:
                # `finally` roda com ou sem erro — sempre pausamos.
                self._pausa()

            resultados = dados.get("results", [])
            self.log.info("consulta_ok consulta=%s resultados=%d", consulta, len(resultados))
            for item in resultados:
                vaga = self._converter(item)
                if vaga:
                    vagas.append(vaga)
        return vagas

    def _converter(self, item: dict) -> Vaga | None:
        """Transforma um item da API no nosso modelo Vaga."""
        titulo = limpar_html(item.get("title"))
        descricao = limpar_html(item.get("description"))
        # (item.get("company") or {}) evita erro quando "company" vem None.
        empresa = (item.get("company") or {}).get("display_name", "")
        local = (item.get("location") or {}).get("display_name", "")
        return self._criar_vaga(
            titulo=titulo,
            empresa=limpar_html(empresa),
            local=local,
            modalidade=detectar_modalidade(titulo, descricao),
            url=limpar_url(item.get("redirect_url", "")),
            data_publicacao=para_iso_utc(item.get("created")),
            descricao=descricao,
        )
