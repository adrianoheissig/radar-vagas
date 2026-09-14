"""
Cálculo de score (0-100) por palavras-chave.

Todas as comparações são feitas sobre texto normalizado (minúsculo, sem
acento e sem pontuação — veja utils.normalizar), então 'Sênior', 'SENIOR'
e 'sênior.' casam com o mesmo padrão 'senior'.

\\b nas regex é "fronteira de palavra": r"\\bjava\\b" casa com "java" mas
não com "javascript".
"""

import re

from collector import config
from collector.models import Vaga
from collector.utils import normalizar

# Padrões especiais para skills cujo nome sozinho gera falso positivo ou
# que aparecem com variações. Skills fora deste dict usam r"\b<nome>\b".
PADROES_SKILL = {
    # Após normalizar, "node.js" vira "node js" e "React.js" vira "react js".
    "node": r"\bnode(js)?\b",
    "react": r"\breact(js)?\b",
    "angular": r"\bangular(js)?\b",
    # Evita "java script" escrito separado.
    "java": r"\bjava\b(?! script)",
}

# Termos que descartam a vaga quando aparecem no TÍTULO.
PADROES_DESCARTE = [
    r"\bsenior\b",
    r"\bsr\b",            # "Sr." vira "sr" após normalizar
    r"\bespecialista\b",
    r"\btech lead\b",
    r"\barquitet[oa]\b",
    r"\bestagio\b",
    r"\bestagiari[oa]\b",
]

# Senioridades compatíveis com o perfil.
PADROES_SENIORIDADE_OK = [r"\bjunior\b", r"\bjr\b", r"\bpleno\b"]

# Outras menções de nível/cargo que NÃO dão bônus de senioridade
# (mas também não descartam a vaga).
PADROES_OUTRAS_SENIORIDADES = [
    r"\btrainee\b", r"\blead\b", r"\blider\b", r"\bcoordenador[a]?\b",
    r"\bgerente\b", r"\bhead\b", r"\bprincipal\b", r"\bstaff\b",
]


def _casa_algum(padroes: list[str], texto: str) -> bool:
    """True se QUALQUER padrão da lista for encontrado no texto.

    any() recebe um "gerador" e para no primeiro True (curto-circuito).
    """
    return any(re.search(p, texto) for p in padroes)


def _pontuar_skills(skills: list[str], texto: str, pontos: int, maximo: int) -> int:
    encontradas = [
        s for s in skills
        if re.search(PADROES_SKILL.get(s, rf"\b{re.escape(s)}\b"), texto)
    ]
    return min(len(encontradas) * pontos, maximo)


def deve_descartar(titulo: str) -> bool:
    """True se o título indica senioridade/cargo incompatível com o perfil."""
    return _casa_algum(PADROES_DESCARTE, normalizar(titulo))


def calcular_score(vaga: Vaga) -> int:
    """Calcula o score da vaga seguindo as regras do README."""
    titulo = normalizar(vaga.titulo)
    texto = f"{titulo} {normalizar(vaga.descricao)}"
    local = normalizar(vaga.local)

    score = 0

    # Skills (título + descrição)
    score += _pontuar_skills(config.SKILLS_PRINCIPAIS, texto,
                             config.PONTOS_SKILL_PRINCIPAL, config.MAX_SKILL_PRINCIPAL)
    score += _pontuar_skills(config.SKILLS_SECUNDARIAS, texto,
                             config.PONTOS_SKILL_SECUNDARIA, config.MAX_SKILL_SECUNDARIA)

    # Localização
    if "guarulhos" in local:
        score += config.PONTOS_GUARULHOS

    # Modalidade
    if vaga.modalidade == "remoto" or (
        vaga.modalidade == "hibrido" and "sao paulo" in local
    ):
        score += config.PONTOS_MODALIDADE

    # Senioridade: bônus se é júnior/pleno OU se o título não menciona nível.
    menciona_ok = _casa_algum(PADROES_SENIORIDADE_OK, titulo)
    menciona_outro = _casa_algum(PADROES_DESCARTE + PADROES_OUTRAS_SENIORIDADES, titulo)
    if menciona_ok or not menciona_outro:
        score += config.PONTOS_SENIORIDADE

    # Descarte (-100): limitamos a 100 ANTES de subtrair, então uma vaga
    # descartada sempre termina em 0, mesmo que tenha somado 110 pontos.
    score = min(100, score)
    if deve_descartar(vaga.titulo):
        score -= 100

    return max(0, score)


def aprovada(vaga: Vaga) -> bool:
    """True se a vaga deve entrar no painel."""
    return not deve_descartar(vaga.titulo) and vaga.score >= config.SCORE_MINIMO
