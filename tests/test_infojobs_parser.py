"""Testa o parsing do HTML do InfoJobs com um card de exemplo (sem acessar a rede)."""

from collector import config
from collector.perfil import Perfil
from collector.sources.infojobs import InfoJobsFonte

HTML_CARD = """
<div class="js_vacanciesGridFragment">
  <div class="card js_rowCard">
    <div id="vacancy123" data-id="123" class="pt-24 px-24 js_vacancyLoad js_rowCard js_cardLink"
         data-href="/vaga-de-desenvolvedora-front-end-em-guarulhos__123.aspx">
      <div class="d-flex flex-wrap gap-8">
        <div hidden class="js_date" data-value="2026/09/13 09:30:00"><span>NOVA</span></div>
      </div>
      <div class="d-flex gap-8 justify-content-between">
        <a href="/vaga-de-desenvolvedora-front-end-em-guarulhos__123.aspx">
          <h2 class="h3 js_vacancyTitle">Desenvolvedor(a) Front-End J&#xFA;nior</h2>
        </a>
      </div>
      <div class="d-flex align-items-baseline">
        <div class="mr-8"><span>4,3</span></div>
        <div class="text-body"><a href="https://www.infojobs.com.br/acme">ACME Tecnologia</a></div>
      </div>
      <div class="mb-8">
        Guarulhos - SP<span hidden class="js_divUserVagaDistance">, <span>0</span> Km de você.</span>
      </div>
      <div class="d-inline-flex flex-wrap mb-8 text-medium">
        <div><svg class="icon"><use xlink:href="#house-and-building" /></svg> H&#xED;brido</div>
      </div>
      <div class="text-medium">Vaga com React e TypeScript...</div>
    </div>
  </div>
</div>
"""


def test_extrai_campos_do_card():
    vagas = InfoJobsFonte()._extrair_vagas(HTML_CARD)
    assert len(vagas) == 1
    vaga = vagas[0]
    assert vaga.titulo == "Desenvolvedor(a) Front-End Júnior"
    assert vaga.empresa == "ACME Tecnologia"
    assert vaga.local == "Guarulhos - SP"
    assert vaga.modalidade == "hibrido"
    assert vaga.url == "https://www.infojobs.com.br/vaga-de-desenvolvedora-front-end-em-guarulhos__123.aspx"
    # 09:30 em Brasília = 12:30 UTC
    assert vaga.data_publicacao == "2026-09-13T12:30:00Z"
    assert "React" in vaga.descricao
    assert vaga.fonte == "infojobs"


def test_html_sem_cards_retorna_lista_vazia():
    assert InfoJobsFonte()._extrair_vagas("<html><body>nada</body></html>") == []


HTML_DETALHE = """
<html><body>
<div class="pt-24 text-medium js_vacancyDataPanels js_applyVacancyHidden">
  <p class="mb-16 text-break white-space-pre-line">Buscamos pessoa desenvolvedora.
Requisitos: React, TypeScript e Node.js. Trabalho híbrido.
Habilidades Necessárias:
Habilidade</p>
  <p>Número de vagas: 1</p>
  <div class="h4">Valorizado</div>
  <div class="mb-32">Experiência desejada: Entre 3 e 5 anos</div>
  <div class="h4">Habilidades</div>
  <div class="d-flex flex-wrap mb-32"><span>Docker</span> <span>Git</span></div>
  <form>Denunciar vaga</form>
</div>
<div class="js_vacancyTitle">Outra vaga similar</div>
</body></html>
"""


def test_extrai_descricao_completa_do_detalhe():
    texto = InfoJobsFonte()._extrair_detalhe(HTML_DETALHE)
    assert "React, TypeScript e Node.js" in texto
    assert "Entre 3 e 5 anos" in texto
    assert "Docker" in texto
    assert "Denunciar" not in texto
    assert "Habilidades Necessárias" not in texto
    assert "Outra vaga similar" not in texto


def test_detalhe_sem_painel_retorna_vazio():
    assert InfoJobsFonte()._extrair_detalhe("<html></html>") == ""


class InfoJobsFalso(InfoJobsFonte):
    """InfoJobs sem rede: devolve HTML fixo e conta as páginas abertas."""

    def __init__(self, *args, falhar=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.detalhes_abertos = []
        self.falhar = falhar

    def _pausa(self):
        pass

    def _baixar_html(self, url, palavra):
        return HTML_CARD.replace("Front-End J&#xFA;nior", "Front-End S&#xEA;nior") if "remoto" in palavra \
            else HTML_CARD

    def _baixar_detalhe(self, url):
        self.detalhes_abertos.append(url)
        if self.falhar:
            raise TimeoutError("sem resposta")
        return HTML_DETALHE


PERFIL = Perfil(termos_busca=["react", "angular"], niveis_aceitos=["junior", "pleno"])


def test_fetch_abre_cada_url_uma_vez_e_troca_resumo_pela_descricao():
    fonte = InfoJobsFalso(PERFIL)
    vagas = fonte.fetch()
    # 2 termos x (busca SP + busca remoto): o card júnior aparece 2 vezes, o sênior 2 vezes.
    assert len(vagas) == 4
    # O card júnior é aberto uma vez só; o sênior é descartado pelo título e nem é aberto.
    assert fonte.detalhes_abertos == [
        "https://www.infojobs.com.br/vaga-de-desenvolvedora-front-end-em-guarulhos__123.aspx"
    ]
    juniores = [v for v in vagas if "Júnior" in v.titulo]
    assert all("Entre 3 e 5 anos" in v.descricao for v in juniores)
    seniores = [v for v in vagas if "Sênior" in v.titulo]
    assert all(v.descricao == "Vaga com React e TypeScript..." for v in seniores)


def test_fetch_mantem_resumo_se_detalhe_falhar():
    vagas = InfoJobsFalso(PERFIL, falhar=True).fetch()
    assert all(v.descricao == "Vaga com React e TypeScript..." for v in vagas)


def test_fetch_respeita_limite_de_detalhes(monkeypatch):
    monkeypatch.setattr(config, "INFOJOBS_MAX_DETALHES", 0)
    fonte = InfoJobsFalso(PERFIL)
    fonte.fetch()
    assert fonte.detalhes_abertos == []
