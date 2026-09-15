"""
Testes do cálculo de score e da análise vaga x perfil.

Os testes usam um perfil FIXO (PERFIL), e não o perfil.json real, para não
quebrarem quando você editar o perfil.

Rodar:  pytest -v
"""

import pytest

from collector.models import Vaga
from collector.perfil import Perfil
from collector.scoring import (
    analisar,
    aprovada,
    calcular_score,
    deve_descartar,
    experiencia_exigida,
)

PERFIL = Perfil(
    anos_experiencia=3,
    niveis_aceitos=["junior", "pleno"],
    skills_principais=["react", "angular", "typescript", "node"],
    skills_secundarias=["java", "mysql", "firebase", "figma"],
    skills_conhecidas=["html", "css", "git"],
    cidades_presencial=["Guarulhos"],
    cidades_hibrido=["São Paulo"],
    aceita_remoto=True,
    termos_busca=["react"],
)


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


def score(**campos) -> int:
    return analisar(criar_vaga(**campos), PERFIL).score


# ---------------------------------------------------------------------------
# Regras básicas
# ---------------------------------------------------------------------------

def test_sem_nenhum_criterio_so_ganha_bonus_de_senioridade():
    assert score() == 15


def test_skills_principais_somam_15_cada_com_teto_45():
    # 4 skills x 15 = 60, mas o teto é 45. +15 de senioridade.
    assert score(descricao="React, Angular, TypeScript e Node.js") == 45 + 15


def test_skills_secundarias_somam_10_cada_com_teto_20():
    assert score(descricao="Java, MySQL, Firebase e Figma") == 20 + 15


def test_javascript_nao_conta_como_java():
    assert score(descricao="JavaScript avançado") == 15


def test_skill_implicita_pontua_nextjs_conta_como_react():
    assert score(descricao="Experiência com Next.js") == 15 + 15


def test_cidade_presencial_ganha_20():
    assert score(local="Guarulhos, SP") == 20 + 15


def test_remoto_ganha_10():
    assert score(modalidade="remoto") == 10 + 15


def test_remoto_nao_pontua_se_perfil_nao_aceita():
    perfil = Perfil(**{**PERFIL.__dict__, "aceita_remoto": False})
    assert analisar(criar_vaga(modalidade="remoto"), perfil).score == 15


@pytest.mark.parametrize("local, esperado", [
    ("São Paulo, SP", 25),
    ("São Paulo, Estado de São Paulo", 25),
    ("Campinas, SP", 15),
    # Estado com o nome "São Paulo" não é a cidade de São Paulo.
    ("Campinas, Estado de São Paulo", 15),
    ("Campinas, São Paulo", 15),
    ("Estado de São Paulo", 15),
])
def test_hibrido_so_ganha_na_cidade_de_sao_paulo(local, esperado):
    assert score(modalidade="hibrido", local=local) == esperado


# ---------------------------------------------------------------------------
# Senioridade
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("titulo", [
    "Desenvolvedor Web Júnior",
    "Dev Frontend Jr",
    "Desenvolvedora Fullstack Pleno",
    "DESENVOLVEDOR FULLSTACK PL",
])
def test_junior_e_pleno_ganham_bonus(titulo):
    assert score(titulo=titulo) == 15


def test_outro_nivel_nao_ganha_bonus_de_senioridade():
    assert score(titulo="Trainee Desenvolvimento") == 0


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
    vaga = analisar(criar_vaga(
        titulo=titulo,
        local="Guarulhos, SP",
        modalidade="remoto",
        descricao="react angular typescript node java mysql",
    ), PERFIL)
    assert deve_descartar(titulo, PERFIL)
    assert vaga.score == 0
    assert not aprovada(vaga, PERFIL)


def test_niveis_aceitos_vem_do_perfil():
    senior = Perfil(**{**PERFIL.__dict__, "niveis_aceitos": ["pleno", "senior"]})
    assert not deve_descartar("Desenvolvedor React Sênior", senior)
    assert deve_descartar("Desenvolvedor React Júnior", senior)


def test_sr_no_meio_de_palavra_nao_descarta():
    assert not deve_descartar("Desenvolvedor Node para SRV Israel", PERFIL)


def test_score_maximo_e_100():
    # 45 + 20 + 20 + 10 + 15 = 110 -> limitado a 100
    assert score(
        titulo="Desenvolvedora Fullstack Júnior",
        local="Guarulhos, SP",
        modalidade="remoto",
        descricao="react angular typescript node java mysql firebase figma",
    ) == 100


def test_score_minimo_para_aprovar():
    ok = analisar(criar_vaga(descricao="react"), PERFIL)   # 15 + 15 = 30
    ruim = analisar(criar_vaga(titulo="Trainee"), PERFIL)   # 0
    assert ok.score == 30 and aprovada(ok, PERFIL)
    assert not aprovada(ruim, PERFIL)


# ---------------------------------------------------------------------------
# Experiência exigida
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("texto, anos", [
    ("Requisitos: 3 anos de experiência com React", 3),
    ("Experiência mínima de 5 anos em desenvolvimento", 5),
    ("5+ anos de experiência", 5),
    ("mínimo de 4 anos atuando com Angular", 4),
    ("entre 2 e 4 anos de experiência", 4),   # "4 anos de experiência" também casa
    ("Empresa com 30 anos de experiência no mercado", None),
    ("Temos 8 anos de experiência no mercado", None),
    ("Vaga sem requisito de tempo", None),
])
def test_experiencia_exigida(texto, anos):
    assert experiencia_exigida(texto) == anos


@pytest.mark.parametrize("descricao, penalidade", [
    ("2 anos de experiência", 0),
    ("4 anos de experiência", 0),    # dentro da tolerância (3 + 1)
    ("5 anos de experiência", 15),
    ("6 anos de experiência", 15),
    ("7 anos de experiência", 30),
    ("10 anos de experiência", 30),  # penalidade máxima
])
def test_penalidade_por_experiencia(descricao, penalidade):
    base = 15 + 15  # "react" + senioridade
    vaga = analisar(criar_vaga(descricao=f"React. {descricao}"), PERFIL)
    assert vaga.score == max(0, base - penalidade)


# ---------------------------------------------------------------------------
# Combina / falta
# ---------------------------------------------------------------------------

def test_skills_match_e_lacunas():
    vaga = analisar(criar_vaga(
        descricao="Stack: React, Next.js, TypeScript, Docker, AWS e Git. Inglês intermediário.",
    ), PERFIL)
    assert vaga.skills_match == ["React", "TypeScript", "Git"]
    assert vaga.lacunas == ["Next.js", "Docker", "AWS", "Inglês"]


def test_skill_implicita_do_perfil_nao_vira_lacuna():
    # O perfil não cita JavaScript, mas quem sabe TypeScript/React sabe JavaScript.
    vaga = analisar(criar_vaga(descricao="JavaScript e HTML"), PERFIL)
    assert vaga.lacunas == []
    assert vaga.skills_match == ["JavaScript", "HTML"]


def test_calcular_score_sem_skills_pre_calculadas():
    vaga = criar_vaga(descricao="react")
    assert calcular_score(vaga, PERFIL) == 30
