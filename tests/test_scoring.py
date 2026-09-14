"""
Testes do cálculo de score.

O pytest descobre automaticamente arquivos test_*.py e funções test_*.
Basta usar `assert` — se a expressão for falsa, o teste falha.

Rodar:  pytest -v
"""

import pytest

from collector.models import Vaga
from collector.scoring import aprovada, calcular_score, deve_descartar


def criar_vaga(**campos) -> Vaga:
    """Fábrica de vagas com valores padrão; os testes sobrescrevem o que precisam."""
    padrao = {
        "titulo": "Desenvolvedor",
        "empresa": "ACME",
        "url": "https://exemplo.com/vaga",
        "fonte": "teste",
        "local": "Curitiba, PR",
        "modalidade": "presencial",
        "descricao": "",
    }
    padrao.update(campos)
    return Vaga(**padrao)


def test_sem_nenhum_criterio_so_ganha_bonus_de_senioridade():
    # Título sem nível -> +15, nada mais.
    assert calcular_score(criar_vaga()) == 15


def test_skills_principais_somam_15_cada_com_teto_45():
    vaga = criar_vaga(descricao="React, Angular, TypeScript e Node.js")
    # 4 skills x 15 = 60, mas o teto é 45. +15 de senioridade.
    assert calcular_score(vaga) == 45 + 15


def test_skills_secundarias_somam_10_cada_com_teto_20():
    vaga = criar_vaga(descricao="Java, MySQL, Firebase e Figma")
    assert calcular_score(vaga) == 20 + 15


def test_javascript_nao_conta_como_java():
    vaga = criar_vaga(descricao="JavaScript avançado")
    assert calcular_score(vaga) == 15


def test_guarulhos_ganha_20():
    vaga = criar_vaga(local="Guarulhos, SP")
    assert calcular_score(vaga) == 20 + 15


def test_remoto_ganha_10():
    assert calcular_score(criar_vaga(modalidade="remoto")) == 10 + 15


def test_hibrido_so_ganha_se_for_em_sao_paulo():
    em_sp = criar_vaga(modalidade="hibrido", local="São Paulo, SP")
    fora = criar_vaga(modalidade="hibrido", local="Campinas, SP")
    assert calcular_score(em_sp) == 10 + 15
    assert calcular_score(fora) == 15


# @pytest.mark.parametrize roda o mesmo teste com vários valores.
@pytest.mark.parametrize("titulo", [
    "Desenvolvedor Web Júnior",
    "Dev Frontend Jr",
    "Desenvolvedora Fullstack Pleno",
])
def test_junior_e_pleno_ganham_bonus(titulo):
    assert calcular_score(criar_vaga(titulo=titulo)) == 15


def test_outro_nivel_nao_ganha_bonus_de_senioridade():
    assert calcular_score(criar_vaga(titulo="Trainee Desenvolvimento")) == 0


@pytest.mark.parametrize("titulo", [
    "Desenvolvedor React Sênior",
    "Desenvolvedor Angular SENIOR",
    "Dev Frontend Sr.",
    "Especialista Frontend",
    "Tech Lead Fullstack",
    "Arquiteto de Software",
    "Estágio em Desenvolvimento",
    "Estagiário Frontend",
    "Desenvolvedor Pleno/Sênior",
])
def test_titulos_descartados(titulo):
    vaga = criar_vaga(
        titulo=titulo,
        local="Guarulhos, SP",
        modalidade="remoto",
        descricao="react angular typescript node java mysql",
    )
    vaga.score = calcular_score(vaga)
    assert deve_descartar(titulo)
    assert vaga.score == 0
    assert not aprovada(vaga)


def test_sr_no_meio_de_palavra_nao_descarta():
    # "srv" ou "Israel" não devem ser confundidos com "Sr."
    assert not deve_descartar("Desenvolvedor Node para SRV Israel")


def test_score_maximo_e_100():
    vaga = criar_vaga(
        titulo="Desenvolvedora Fullstack Júnior",
        local="Guarulhos, SP",
        modalidade="remoto",
        descricao="react angular typescript node java mysql firebase figma",
    )
    # 45 + 20 + 20 + 10 + 15 = 110 -> limitado a 100
    assert calcular_score(vaga) == 100


def test_score_minimo_para_aprovar():
    abaixo = criar_vaga(descricao="react")          # 15 + 15 = 30 -> aprova
    muito_abaixo = criar_vaga(titulo="Trainee")     # 0 -> reprova
    abaixo.score = calcular_score(abaixo)
    muito_abaixo.score = calcular_score(muito_abaixo)
    assert abaixo.score == 30 and aprovada(abaixo)
    assert not aprovada(muito_abaixo)
