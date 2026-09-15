"""
Fonte: InfoJobs Brasil — scraping da página de busca com requests + BeautifulSoup.

Páginas usadas:
  https://www.infojobs.com.br/empregos-em-sao-paulo.aspx?palabra=<termo>  (estado de SP)
  https://www.infojobs.com.br/empregos.aspx?palabra=<termo>+remoto        (Brasil todo)

Hoje (set/2026) o HTML da busca vem renderizado do servidor, então não
precisamos de navegador. Cada vaga é um <div class="... js_vacancyLoad ...">.

Scraping é frágil: se o InfoJobs mudar o HTML, os seletores abaixo quebram
e a fonte passa a retornar 0 vagas (o log mostra). Não há login nem
candidatura aqui — apenas leitura da busca pública.

---------------------------------------------------------------------------
SE A PÁGINA PASSAR A EXIGIR JAVASCRIPT (a busca vier sem cards):
  1. Desative em config.FONTES_ATIVAS["infojobs"] = False.
  2. Para reativar com Playwright:
       pip install playwright && playwright install chromium
     e troque o `_baixar_html` por algo como:

       from playwright.sync_api import sync_playwright
       with sync_playwright() as p:
           navegador = p.chromium.launch()
           pagina = navegador.new_page()
           pagina.goto(url, wait_until="networkidle")
           html = pagina.content()
           navegador.close()

     O parsing com BeautifulSoup (`_extrair_vagas`) continua igual.
  3. No workflow do GitHub Actions, adicione o passo
       `python -m playwright install --with-deps chromium`.
---------------------------------------------------------------------------
"""

from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from collector.models import Vaga
from collector.sources.base import Fonte
from collector.utils import FUSO_BRASILIA, detectar_modalidade, limpar_espacos, para_iso_utc

URL_BASE = "https://www.infojobs.com.br"
URL_BUSCA_SP = f"{URL_BASE}/empregos-em-sao-paulo.aspx"
URL_BUSCA_BRASIL = f"{URL_BASE}/empregos.aspx"

MAPA_MODALIDADE = {
    "remoto": "remoto",
    "home office": "remoto",
    "hibrido": "hibrido",
    "híbrido": "hibrido",
    "presencial": "presencial",
}


class InfoJobsFonte(Fonte):
    nome = "infojobs"

    def fetch(self) -> list[Vaga]:
        vagas: list[Vaga] = []
        for termo in self.perfil.termos_busca:
            # Tupla de tuplas: (url, termo usado na busca)
            buscas = (
                (URL_BUSCA_SP, termo),
                (URL_BUSCA_BRASIL, f"{termo} remoto"),
            )
            for url, palavra in buscas:
                try:
                    html = self._baixar_html(url, palavra)
                except Exception as erro:  # noqa: BLE001
                    self.log.warning("consulta_falhou termo=%r erro=%s", palavra, erro)
                    continue
                finally:
                    self._pausa()

                encontradas = self._extrair_vagas(html)
                self.log.info("consulta_ok url=%s termo=%r resultados=%d",
                              url, palavra, len(encontradas))
                vagas.extend(encontradas)
        return vagas

    def _baixar_html(self, url: str, palavra: str) -> str:
        return self._get(url, params={"palabra": palavra}).text

    # ------------------------------------------------------------------
    # Parsing — separado do download para ser testável com HTML salvo.
    # ------------------------------------------------------------------

    def _extrair_vagas(self, html: str) -> list[Vaga]:
        sopa = BeautifulSoup(html, "html.parser")
        vagas = []
        # select() usa seletores CSS, igual document.querySelectorAll.
        for card in sopa.select("div.js_vacancyLoad"):
            try:
                vaga = self._converter_card(card)
            except Exception as erro:  # noqa: BLE001 - um card estranho não derruba a página
                self.log.debug("card_ignorado erro=%s", erro)
                continue
            if vaga:
                vagas.append(vaga)
        return vagas

    def _converter_card(self, card: Tag) -> Vaga | None:
        titulo_tag = card.select_one(".js_vacancyTitle")
        href = card.get("data-href")
        if not titulo_tag or not href:
            return None

        # Empresa: <div class="d-flex align-items-baseline"> > <div class="text-body">
        empresa_tag = card.select_one(".align-items-baseline > .text-body")
        empresa = empresa_tag.get_text(" ", strip=True) if empresa_tag else ""

        # Local: <div class="mb-8">São Paulo - SP<span hidden>...</span></div>
        # Procuramos o div cuja classe é exatamente "mb-8" e pegamos só o
        # primeiro texto (antes do <span> escondido com a distância).
        local = ""
        for div in card.find_all("div", recursive=False):
            if div.get("class") == ["mb-8"]:
                local = limpar_espacos(next(div.stripped_strings, ""))
                break

        # Modalidade: o texto ao lado do ícone "house-and-building".
        modalidade = "indefinido"
        icone = card.find("use", attrs={"xlink:href": "#house-and-building"})
        if icone:
            div_modalidade = icone.find_parent("div")
            if div_modalidade:
                texto = div_modalidade.get_text(" ", strip=True).lower()
                modalidade = MAPA_MODALIDADE.get(texto, "indefinido")

        # Resumo da descrição: div com classe exatamente "text-medium".
        descricao = ""
        for div in card.find_all("div", recursive=False):
            if div.get("class") == ["text-medium"]:
                descricao = div.get_text(" ", strip=True)

        if modalidade == "indefinido":
            modalidade = detectar_modalidade(titulo_tag.get_text(), descricao)

        # Data: <div hidden class="js_date" data-value="2026/07/13 01:12:00">
        data_tag = card.select_one(".js_date")
        data_publicacao = None
        if data_tag and data_tag.get("data-value"):
            data_publicacao = para_iso_utc(data_tag["data-value"], "%Y/%m/%d %H:%M:%S",
                                           fuso_padrao=FUSO_BRASILIA)

        return self._criar_vaga(
            titulo=titulo_tag.get_text(" ", strip=True),
            empresa=empresa,
            local=local,
            modalidade=modalidade,
            url=urljoin(URL_BASE, href),
            data_publicacao=data_publicacao,
            descricao=descricao,
        )
