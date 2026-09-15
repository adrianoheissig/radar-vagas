"""Testes do dicionário de skills e da geração do perfil a partir do currículo.

Usa um currículo FICTÍCIO em texto (sem PDF e sem dados reais).
"""

import json
from datetime import date

import pytest

from collector import skills
from collector.perfil import (
    Perfil,
    carregar,
    detectar_anos,
    detectar_cidade,
    gerar_de_texto,
    main,
    niveis_por_anos,
    salvar,
    secao,
)

CURRICULO = """JOANA EXEMPLO
RESUMO PROFISSIONAL
Desenvolvedora Full Stack com foco em Frontend, com cerca de 4 anos de experiência
em Vue.js e TypeScript, além de Python com Django na construção de APIs RESTful.
EXPERIÊNCIA:
Desenvolvedora Fullstack
Empresa Exemplo2021 - Atualmente
Criação de telas com Vue, Tailwind e testes com Jest. Deploy com Docker.
Campinas, SP | (19) 99999-0000 | joana@exemplo.com
HABILIDADES TÉCNICAS:
Backend:
PostgreSQL: Intermediário
Git: Avançado
FORMAÇÃO ACADÊMICA:
Ciência da Computação — 2020
"""


# ---------------------------------------------------------------------------
# skills.py
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("texto, esperado", [
    ("React.JS e ReactJS", ["React"]),
    ("React Native", ["React Native"]),
    ("JavaScript e Java", ["JavaScript", "Java"]),
    ("C# com .NET e CI/CD", ["C#", ".NET", "CI/CD"]),
    ("Node.js, NodeJs e node", ["Node.js"]),
    ("construção de microsserviços", ["Microsserviços"]),
    ("PL/SQL e SQL Server", ["SQL", "Oracle", "SQL Server"]),
    ("restante e interesse", []),
])
def test_detectar_skills(texto, esperado):
    assert skills.rotulos(skills.detectar(texto)) == esperado


def test_expandir_segue_cadeia_de_implicacoes():
    # nextjs -> react -> javascript
    assert skills.expandir({"nextjs"}) == {"nextjs", "react", "javascript"}


# ---------------------------------------------------------------------------
# Leitura do currículo
# ---------------------------------------------------------------------------

def test_secao_para_no_proximo_titulo():
    resumo = secao(CURRICULO, "resumo")
    assert "Vue.js" in resumo
    assert "Empresa Exemplo" not in resumo


def test_anos_pela_frase_explicita():
    assert detectar_anos(CURRICULO) == 4


def test_anos_pelos_periodos_quando_nao_ha_frase():
    texto = "EXPERIÊNCIA:\nEmpresa A2019 - 2021\nEmpresa B 2021 - Atualmente\nFORMAÇÃO:\nCurso 2010 - 2014"
    assert detectar_anos(texto, hoje=date(2026, 9, 15)) == 7


def test_cidade():
    assert detectar_cidade(CURRICULO) == ("Campinas", "SP")
    assert detectar_cidade("Mora em São José dos Campos - SP") == ("São José dos Campos", "SP")
    assert detectar_cidade("sem endereço") is None


@pytest.mark.parametrize("anos, niveis", [
    (None, ["junior", "pleno"]), (1, ["junior"]), (3, ["junior", "pleno"]), (8, ["pleno", "senior"]),
])
def test_niveis_por_anos(anos, niveis):
    assert niveis_por_anos(anos) == niveis


def test_gerar_perfil_de_texto():
    perfil = gerar_de_texto(CURRICULO)
    assert perfil.anos_experiencia == 4
    assert perfil.niveis_aceitos == ["junior", "pleno"]
    # Principais: citadas no resumo, na ordem em que aparecem (sem as "comuns").
    assert perfil.skills_principais == ["vue", "typescript", "python", "django"]
    assert "postgresql" in perfil.skills_secundarias
    assert "git" not in perfil.skills_secundarias          # comum: não pontua
    assert "git" in perfil.skills_conhecidas
    assert perfil.cidades_presencial == ["Campinas"]
    assert perfil.cidades_hibrido == ["São Paulo"]
    # "Backend:" nas habilidades NÃO vira termo de busca (só o resumo conta).
    assert perfil.termos_busca == ["desenvolvedor fullstack", "desenvolvedor frontend", "vue.js", "typescript", "python"]
    assert len(perfil.consultas_jsearch) == 2


def test_perfil_gerado_nao_tem_dados_pessoais(tmp_path):
    arquivo = tmp_path / "perfil.json"
    salvar(gerar_de_texto(CURRICULO), arquivo)
    conteudo = arquivo.read_text(encoding="utf-8").lower()
    for dado in ("joana", "exemplo.com", "99999", "(19)"):
        assert dado not in conteudo


# ---------------------------------------------------------------------------
# Arquivo perfil.json
# ---------------------------------------------------------------------------

def test_carregar_sem_arquivo_usa_padrao(tmp_path):
    perfil = carregar(tmp_path / "nao-existe.json")
    assert perfil.skills_principais == Perfil.padrao().skills_principais


def test_carregar_ignora_chaves_extras_e_corta_cotas(tmp_path):
    arquivo = tmp_path / "perfil.json"
    arquivo.write_text(json.dumps({
        "_leia_me": "texto de ajuda",
        "skills_principais": ["react"],
        "termos_busca": [f"termo {i}" for i in range(9)],
        "consultas_jsearch": ["a", "b", "c"],
    }), encoding="utf-8")
    perfil = carregar(arquivo)
    assert perfil.skills_principais == ["react"]
    assert len(perfil.termos_busca) == 5
    assert len(perfil.consultas_jsearch) == 2


def test_localidades_busca_sem_repeticao():
    perfil = Perfil(cidades_hibrido=["São Paulo"], cidades_presencial=["Sao Paulo", "Guarulhos"])
    assert perfil.localidades_busca() == ["São Paulo", "Guarulhos"]


def test_cli_nao_sobrescreve_sem_flag(tmp_path, capsys):
    curriculo = tmp_path / "cv.txt"
    curriculo.write_text(CURRICULO, encoding="utf-8")
    saida = tmp_path / "perfil.json"

    assert main(["gerar", str(curriculo), "--saida", str(saida)]) == 0
    assert saida.exists()
    assert main(["gerar", str(curriculo), "--saida", str(saida)]) == 1
    assert main(["gerar", str(curriculo), "--saida", str(saida), "--sobrescrever"]) == 0
