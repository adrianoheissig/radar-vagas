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
# Termos de busca
# ---------------------------------------------------------------------------

TERMOS_BUSCA = [
    "desenvolvedor frontend",
    "desenvolvedor fullstack",
    "react",
    "angular",
    "desenvolvedora júnior",
]

# Localidades usadas nas fontes que aceitam filtro de local.
# None significa "sem filtro de local" e é usado para achar vagas remotas.
LOCALIDADES = ["São Paulo", "Guarulhos"]

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
# Com 3 execuções por dia (~90/mês), cabem 2 consultas por execução.
# Se aumentar esta lista, a cota acaba antes do fim do mês.
JSEARCH_CONSULTAS = [
    "desenvolvedor frontend react angular em São Paulo",
    "desenvolvedor fullstack júnior remoto Brasil",
]

# ---------------------------------------------------------------------------
# Score
# ---------------------------------------------------------------------------

SKILLS_PRINCIPAIS = ["react", "angular", "typescript", "node"]
PONTOS_SKILL_PRINCIPAL = 15
MAX_SKILL_PRINCIPAL = 45

SKILLS_SECUNDARIAS = ["java", "mysql", "firebase", "figma"]
PONTOS_SKILL_SECUNDARIA = 10
MAX_SKILL_SECUNDARIA = 20

PONTOS_GUARULHOS = 20
PONTOS_MODALIDADE = 10
PONTOS_SENIORIDADE = 15

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
