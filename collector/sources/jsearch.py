"""
Fonte: JSearch (RapidAPI) — agrega Google for Jobs (Indeed, LinkedIn, Glassdoor...).

Documentação: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
Endpoint:     GET https://jsearch.p.rapidapi.com/search

OPCIONAL: se RAPIDAPI_KEY não estiver definida, a fonte é pulada.
Atenção à cota do plano gratuito (~200 requisições/mês) — veja
config.JSEARCH_CONSULTAS.
"""

import os

from collector import config
from collector.models import Vaga
from collector.sources.base import Fonte
from collector.utils import detectar_modalidade, limpar_html, para_iso_utc

HOST = "jsearch.p.rapidapi.com"
URL_BUSCA = f"https://{HOST}/search"


class JSearchFonte(Fonte):
    nome = "jsearch"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.api_key = os.environ.get("RAPIDAPI_KEY", "").strip()

    def disponivel(self) -> bool:
        if not self.api_key:
            self.log.warning("fonte_pulada motivo=RAPIDAPI_KEY ausente (fonte opcional)")
            return False
        return True

    def fetch(self) -> list[Vaga]:
        headers = {"X-RapidAPI-Key": self.api_key, "X-RapidAPI-Host": HOST}
        vagas: list[Vaga] = []

        for consulta in config.JSEARCH_CONSULTAS:
            params = {
                "query": consulta,
                "page": 1,
                "num_pages": 1,
                "country": "br",
                "language": "pt",
                "date_posted": "week",
            }
            try:
                dados = self._get(URL_BUSCA, params=params, headers=headers).json()
            except Exception as erro:  # noqa: BLE001
                self.log.warning("consulta_falhou consulta=%r erro=%s",
                                 consulta, type(erro).__name__)
                continue
            finally:
                self._pausa()

            resultados = dados.get("data") or []
            self.log.info("consulta_ok consulta=%r resultados=%d", consulta, len(resultados))
            for item in resultados:
                vaga = self._converter(item)
                if vaga:
                    vagas.append(vaga)
        return vagas

    def _converter(self, item: dict) -> Vaga | None:
        titulo = item.get("job_title", "")
        descricao = limpar_html(item.get("job_description"))
        # filter(None, lista) remove itens vazios/None antes do join.
        local = ", ".join(filter(None, [item.get("job_city"), item.get("job_state")]))
        if item.get("job_is_remote"):
            modalidade = "remoto"
        else:
            modalidade = detectar_modalidade(titulo, descricao)
        return self._criar_vaga(
            titulo=titulo,
            empresa=item.get("employer_name") or "",
            local=local,
            modalidade=modalidade,
            url=item.get("job_apply_link") or item.get("job_google_link") or "",
            data_publicacao=para_iso_utc(item.get("job_posted_at_datetime_utc")),
            descricao=descricao,
        )
