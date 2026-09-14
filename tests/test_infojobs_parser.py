"""Testa o parsing do HTML do InfoJobs com um card de exemplo (sem acessar a rede)."""

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
