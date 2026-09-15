"""
Configurações centrais do coletor.

Tudo que você talvez queira ajustar (termos de busca, pesos do score,
fontes ativas) fica aqui, para não precisar caçar valores pelo código.

Em Python, constantes são só variáveis em MAIÚSCULAS por convenção —
a linguagem não impede que sejam alteradas, é um "acordo entre cavalheiros".
"""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------

# Path(__file__) é o caminho deste arquivo (collector/config.py).
# .resolve().parent.parent sobe dois níveis: collector/ -> raiz do projeto.
RAIZ_PROJETO = Path(__file__).resolve().parent.parent

# os.environ.get(nome, padrao) lê uma variável de ambiente, com valor padrão.
# Permite mudar o destino do JSON sem alterar código (útil no Docker).
ARQUIVO_VAGAS = Path(
    os.environ.get("VAGAS_JSON_PATH", RAIZ_PROJETO / "docs" / "data" / "vagas.json")
)

# Perfil gerado a partir do currículo (python -m collector.perfil gerar ...).
ARQUIVO_PERFIL = Path(os.environ.get("PERFIL_JSON_PATH", RAIZ_PROJETO / "perfil.json"))

# ---------------------------------------------------------------------------
# Liga/desliga de fontes
# ---------------------------------------------------------------------------

# Um dicionário (dict) mapeando nome da fonte -> ativa?
# Para desativar uma fonte sem apagar código, basta trocar para False.
FONTES_ATIVAS = {
    "adzuna": True,
    "jsearch": True,    # só roda se RAPIDAPI_KEY existir
    "gupy": True,
    # O InfoJobs hoje entrega o HTML da busca renderizado no servidor,
    # então requests + BeautifulSoup funciona. Se um dia a página passar
    # a exigir JavaScript, troque para False e veja o comentário em
    # collector/sources/infojobs.py sobre como migrar para Playwright.
    "infojobs": True,
}

# ---------------------------------------------------------------------------
# Valores padrão do perfil
# ---------------------------------------------------------------------------
# Usados SOMENTE quando não existe perfil.json. Com o perfil gerado a partir
# do currículo, termos de busca, skills e cidades vêm de lá.

TERMOS_BUSCA = [
    "desenvolvedor frontend",
    "desenvolvedor fullstack",
    "react",
    "angular",
    "desenvolvedora júnior",
]

# Limites que protegem as cotas gratuitas das APIs:
# a Adzuna faz (termos x (cidades + 1)) chamadas por execução.
MAX_TERMOS_BUSCA = 5
MAX_CONSULTAS_JSEARCH = 2

# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

TIMEOUT_HTTP = 30          # segundos
PAUSA_ENTRE_CHAMADAS = 1.5  # segundos entre requisições à mesma fonte
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36 radar-vagas/1.0"
)

# ---------------------------------------------------------------------------
# JSearch (RapidAPI)
# ---------------------------------------------------------------------------

# O plano gratuito do JSearch dá ~200 requisições/MÊS.
# Com 3 execuções por dia (~90/mês), cabem 2 consultas por execução
# (MAX_CONSULTAS_JSEARCH). Padrão usado quando não há perfil.json.
JSEARCH_CONSULTAS = [
    "desenvolvedor frontend react angular em São Paulo",
    "desenvolvedor fullstack júnior remoto Brasil",
]

# ---------------------------------------------------------------------------
# Score
# ---------------------------------------------------------------------------

# As listas de skills abaixo são o padrão sem perfil.json; os PESOS valem sempre.
SKILLS_PRINCIPAIS = ["react", "angular", "typescript", "node"]
PONTOS_SKILL_PRINCIPAL = 15
MAX_SKILL_PRINCIPAL = 45

SKILLS_SECUNDARIAS = ["java", "mysql", "firebase", "figma"]
PONTOS_SKILL_SECUNDARIA = 10
MAX_SKILL_SECUNDARIA = 20

PONTOS_CIDADE_PRESENCIAL = 20   # local é uma das cidades_presencial do perfil
PONTOS_MODALIDADE = 10
PONTOS_SENIORIDADE = 15

# Experiência exigida na vaga x anos do perfil.
# Ex.: perfil com 3 anos; vaga pede 5 -> -15; vaga pede 7 ou mais -> -30.
EXPERIENCIA_TOLERANCIA = 1      # anos a mais que ainda não penalizam
PENALIDADE_EXPERIENCIA = 15     # por faixa de 2 anos acima da tolerância
MAX_PENALIDADE_EXPERIENCIA = 30

SCORE_MINIMO = 30

# ---------------------------------------------------------------------------
# Histórico
# ---------------------------------------------------------------------------

DIAS_PARA_EXPIRAR = 14   # vaga não vista há mais que isso -> "expirada": true
# Vagas expiradas e não vistas há mais que isso são removidas do JSON,
# para o arquivo não crescer para sempre (o painel roda no celular).
# Use 0 para nunca remover.
DIAS_PARA_REMOVER = 60

TAMANHO_MAX_DESCRICAO = 1500
