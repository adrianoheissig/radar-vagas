"""Testes de deduplicação, histórico e gravação do JSON."""

import json
from datetime import date, timedelta

from collector import storage
from collector.models import Vaga, gerar_id

HOJE = date(2026, 9, 14)


def criar_vaga(titulo="Dev React", empresa="ACME", score=50, **campos) -> Vaga:
    return Vaga(
        titulo=titulo,
        empresa=empresa,
        url=campos.pop("url", f"https://exemplo.com/{titulo}"),
        fonte=campos.pop("fonte", "teste"),
        score=score,
        **campos,
    )


# ---------------------------------------------------------------------------
# id
# ---------------------------------------------------------------------------

def test_id_ignora_maiusculas_acentos_e_pontuacao():
    assert gerar_id("Dev Front-End Júnior", "ACME Ltda.") == gerar_id("dev front end junior", "acme ltda")


def test_id_muda_com_empresa_diferente():
    assert gerar_id("Dev React", "ACME") != gerar_id("Dev React", "Outra")


def test_empresa_vazia_usa_local_no_id():
    assert gerar_id("Dev React", "", "São Paulo") != gerar_id("Dev React", "", "Recife")


# ---------------------------------------------------------------------------
# mesclar
# ---------------------------------------------------------------------------

def test_mesma_vaga_de_duas_fontes_vira_uma_so_com_maior_score():
    a = criar_vaga(fonte="adzuna", score=40)
    b = criar_vaga(empresa="acme", fonte="gupy", score=70)
    resultado = storage.mesclar([], [a, b], hoje=HOJE)
    assert len(resultado) == 1
    assert resultado[0].fonte == "gupy"


def test_vaga_conhecida_mantem_data_coleta_original():
    antiga = criar_vaga(data_coleta="2026-09-01T10:00:00Z", ultima_vista="2026-09-01")
    nova = criar_vaga(data_coleta="2026-09-14T10:00:00Z")
    resultado = storage.mesclar([antiga], [nova], hoje=HOJE)
    assert len(resultado) == 1
    assert resultado[0].data_coleta == "2026-09-01T10:00:00Z"
    assert resultado[0].ultima_vista == HOJE.isoformat()


def test_vaga_nao_vista_ha_mais_de_14_dias_expira_sem_ser_removida():
    velha = criar_vaga(ultima_vista=(HOJE - timedelta(days=15)).isoformat())
    recente = criar_vaga(titulo="Outra", ultima_vista=(HOJE - timedelta(days=14)).isoformat())
    resultado = {v.titulo: v for v in storage.mesclar([velha, recente], [], hoje=HOJE)}
    assert resultado["Dev React"].expirada is True
    assert resultado["Outra"].expirada is False


def test_vaga_expirada_que_reaparece_volta_a_ativa():
    velha = criar_vaga(ultima_vista="2026-08-01", expirada=True)
    resultado = storage.mesclar([velha], [criar_vaga()], hoje=HOJE)
    assert resultado[0].expirada is False


def test_vaga_muito_antiga_e_removida():
    muito_velha = criar_vaga(ultima_vista=(HOJE - timedelta(days=61)).isoformat())
    assert storage.mesclar([muito_velha], [], hoje=HOJE) == []


def test_ordena_por_score_e_depois_data_publicacao():
    vagas = [
        criar_vaga(titulo="A", score=50, data_publicacao="2026-09-01T00:00:00Z"),
        criar_vaga(titulo="B", score=80, data_publicacao="2026-08-01T00:00:00Z"),
        criar_vaga(titulo="C", score=50, data_publicacao="2026-09-10T00:00:00Z"),
        criar_vaga(titulo="D", score=50, data_publicacao=None),
    ]
    resultado = storage.mesclar([], vagas, hoje=HOJE)
    assert [v.titulo for v in resultado] == ["B", "C", "A", "D"]


# ---------------------------------------------------------------------------
# Idempotência de ponta a ponta (mesclar + salvar + carregar)
# ---------------------------------------------------------------------------

def test_rodar_duas_vezes_nao_duplica_nem_regrava(tmp_path):
    # tmp_path é uma "fixture" do pytest: uma pasta temporária por teste.
    arquivo = tmp_path / "vagas.json"

    def coleta():
        # Cada execução cria objetos novos, como aconteceria de verdade.
        return [criar_vaga(titulo="Dev React"), criar_vaga(titulo="Dev Angular")]

    primeira = storage.mesclar(storage.carregar(arquivo), coleta(), hoje=HOJE)
    assert storage.salvar(arquivo, primeira) is True
    conteudo_1 = arquivo.read_text(encoding="utf-8")

    segunda = storage.mesclar(storage.carregar(arquivo), coleta(), hoje=HOJE)
    assert storage.salvar(arquivo, segunda) is False  # nada mudou -> não grava

    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    assert dados["total"] == 2
    assert len({v["id"] for v in dados["vagas"]}) == 2
    assert arquivo.read_text(encoding="utf-8") == conteudo_1


def test_descricao_truncada_ao_salvar(tmp_path):
    arquivo = tmp_path / "vagas.json"
    storage.salvar(arquivo, [criar_vaga(descricao="x" * 5000)])
    vaga = json.loads(arquivo.read_text(encoding="utf-8"))["vagas"][0]
    assert len(vaga["descricao"]) == 1500
    assert list(vaga)[0] == "id"


def test_url_adzuna_sem_parametro_de_sessao():
    from collector.sources.adzuna import limpar_url
    url = "https://www.adzuna.com.br/land/ad/588?se=AbC123&utm_medium=api&v=40C6"
    assert limpar_url(url) == "https://www.adzuna.com.br/land/ad/588?utm_medium=api&v=40C6"
