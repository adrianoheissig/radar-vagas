"""
Fonte: Gupy — API pública usada pelo próprio portal https://portal.gupy.io

Endpoint: GET https://employability-portal.gupy.io/api/v1/jobs
Parâmetros: jobName, limit (até 100), offset, e filtros opcionais
            state, city, workplaceType (remote/hybrid/on-site).

Obs.: o endpoint antigo `https://portal.api.gupy.io/api/job?name=...`
retorna 404; este é o que o portal usa hoje (verificado em
set/2026). Não é uma API documentada — se parar de funcionar, abra o
portal no navegador, busque uma vaga e veja na aba Network do DevTools
qual URL ele chama.
"""

from collector import config
from collector.models import Vaga
from collector.sources.base import Fonte
from collector.utils import limpar_html, para_iso_utc

URL_BUSCA = "https://employability-portal.gupy.io/api/v1/jobs"
LIMITE_POR_PAGINA = 100
MAX_PAGINAS = 3

MAPA_MODALIDADE = {
    "remote": "remoto",
    "hybrid": "hibrido",
    "on-site": "presencial",
}


class GupyFonte(Fonte):
    nome = "gupy"

    def fetch(self) -> list[Vaga]:
        vagas: list[Vaga] = []
        for termo in config.TERMOS_BUSCA:
            vagas.extend(self._buscar_termo(termo))
        return vagas

    def _buscar_termo(self, termo: str) -> list[Vaga]:
        vagas: list[Vaga] = []
        # range(3) gera 0, 1, 2
        for pagina in range(MAX_PAGINAS):
            params = {
                "jobName": termo,
                "limit": LIMITE_POR_PAGINA,
                "offset": pagina * LIMITE_POR_PAGINA,
            }
            try:
                dados = self._get(URL_BUSCA, params=params).json()
            except Exception as erro:  # noqa: BLE001
                self.log.warning("consulta_falhou termo=%r erro=%s", termo, erro)
                break
            finally:
                self._pausa()  # respeita rate limit

            itens = dados.get("data") or []
            total = (dados.get("pagination") or {}).get("total", 0)
            self.log.info("consulta_ok termo=%r pagina=%d resultados=%d total=%d",
                          termo, pagina + 1, len(itens), total)

            for item in itens:
                vaga = self._converter(item)
                if vaga:
                    vagas.append(vaga)

            # Para quando já pegou tudo que existe.
            if (pagina + 1) * LIMITE_POR_PAGINA >= total:
                break
        return vagas

    def _converter(self, item: dict) -> Vaga | None:
        modalidade = MAPA_MODALIDADE.get(item.get("workplaceType", ""), "indefinido")
        local = ", ".join(filter(None, [item.get("city"), item.get("state")]))
        if not local:
            local = "Remoto" if modalidade == "remoto" else (item.get("country") or "")
        return self._criar_vaga(
            titulo=item.get("name", ""),
            # A Gupy expõe o nome da página de carreira, que costuma ser o nome
            # da empresa (às vezes é um slogan).
            empresa=item.get("careerPageName") or "",
            local=local,
            modalidade=modalidade,
            url=item.get("jobUrl", ""),
            data_publicacao=para_iso_utc(item.get("publishedDate")),
            descricao=limpar_html(item.get("description")),
        )
