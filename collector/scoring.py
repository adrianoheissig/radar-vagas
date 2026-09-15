"""
Análise da vaga contra o perfil (gerado a partir do currículo).

Para cada vaga calculamos:
- score (0-100)
- skills_match: skills pedidas na vaga que a candidata tem
- lacunas: skills pedidas na vaga que não aparecem no currículo
- experiencia_exigida: anos pedidos na descrição (quando dá para identificar)

Regras do score:
  +15 por skill principal do perfil citada na vaga (máx. 45)
  +10 por skill secundária do perfil citada na vaga (máx. 20)
  +20 se a vaga é em uma das cidades_presencial do perfil
  +10 se é remota (e o perfil aceita) ou híbrida em uma das cidades_hibrido
  +15 se o título cita um nível aceito ou não cita nível nenhum
  -15/-30 se a vaga pede bem mais anos de experiência do que o perfil tem
  -100 (descarta) se o título cita um nível fora de niveis_aceitos

Comparações usam texto normalizado (minúsculo, sem acento, sem pontuação).
"""

import math
import re

from collector import config, skills
from collector.models import Vaga
from collector.perfil import Perfil
from collector.utils import normalizar

# Menções de nível no TÍTULO. Especialista, tech lead e arquiteto contam
# como "senior" (são cargos acima de pleno).
PADROES_NIVEL = {
    "estagio": [r"\bestagio\b", r"\bestagiari[oa]\b"],
    "junior": [r"\bjunior\b", r"\bjr\b"],
    "pleno": [r"\bpleno\b", r"\bpl\b(?! sql)"],
    "senior": [r"\bsenior\b", r"\bsr\b", r"\bespecialista\b", r"\btech lead\b", r"\barquitet[oa]\b"],
}

# Outras menções de cargo que NÃO dão bônus de senioridade (mas não descartam).
PADROES_OUTRAS_SENIORIDADES = [
    r"\btrainee\b", r"\blead\b", r"\blider\b", r"\bcoordenador[a]?\b",
    r"\bgerente\b", r"\bhead\b", r"\bprincipal\b", r"\bstaff\b",
]

# Anos de experiência pedidos na descrição.
PADROES_EXPERIENCIA = [
    # "3 anos de experiência", "5 ou mais anos de atuação"
    r"(\d{1,2}) (?:ou mais )?anos? (?:de )?(?:experiencia|atuacao|vivencia)"
    r"(?! (?:no|de|em) mercado)",
    # "experiência mínima de 3 anos", "experiência de pelo menos 2 anos"
    r"experiencia (?:minima |comprovada |previa )?(?:de )?(?:no minimo |minimo |pelo menos |acima de |mais de )?"
    r"(\d{1,2}) anos?",
    # "mínimo de 4 anos"
    r"(?:no minimo|minimo|pelo menos) (?:de )?(\d{1,2}) anos?",
    # "entre 3 e 5 anos" -> 3
    r"entre (\d{1,2}) e \d{1,2} anos?",
]
MAX_ANOS_PLAUSIVEL = 10  # acima disso costuma ser "empresa com 30 anos de mercado"


def _casa_algum(padroes: list[str], texto: str) -> bool:
    """True se QUALQUER padrão casar. any() para no primeiro True."""
    return any(re.search(p, texto) for p in padroes)


def niveis_no_titulo(titulo: str) -> set[str]:
    titulo = normalizar(titulo)
    return {nivel for nivel, padroes in PADROES_NIVEL.items() if _casa_algum(padroes, titulo)}


def deve_descartar(titulo: str, perfil: Perfil) -> bool:
    """True se o título cita algum nível fora dos aceitos pelo perfil.

    Ex.: perfil júnior/pleno descarta "Pleno/Sênior", mas mantém "Júnior/Pleno".
    """
    return bool(niveis_no_titulo(titulo) - set(perfil.niveis_aceitos))


def experiencia_exigida(texto: str) -> int | None:
    """Maior número plausível de anos pedido no texto, ou None."""
    norm = normalizar(texto)
    valores = [
        int(n)
        for padrao in PADROES_EXPERIENCIA
        for n in re.findall(padrao, norm)
        if 0 < int(n) <= MAX_ANOS_PLAUSIVEL
    ]
    return max(valores) if valores else None


def _cidade(local: str) -> str:
    """'Campinas, Estado de São Paulo' -> 'campinas'; 'São José dos Campos - SP' -> 'sao jose dos campos'.

    Compara só a CIDADE (primeiro pedaço), para "Campinas, São Paulo" não ser
    confundida com a cidade de São Paulo.
    """
    return normalizar(re.split(r",| - ", local or "", maxsplit=1)[0])


def _pontuar_skills(ids_perfil: list[str], ids_vaga: set[str], pontos: int, maximo: int) -> int:
    return min(sum(1 for s in ids_perfil if s in ids_vaga) * pontos, maximo)


def analisar(vaga: Vaga, perfil: Perfil) -> Vaga:
    """Preenche score, skills_match, lacunas e experiencia_exigida da vaga."""
    texto = f"{vaga.titulo}\n{vaga.descricao}"

    citadas = skills.detectar(texto)            # o que a vaga pede explicitamente
    citadas_expandidas = skills.expandir(citadas)  # + implícitas (Next.js -> React)
    da_candidata = perfil.todas_as_skills()

    vaga.skills_match = skills.rotulos(citadas & da_candidata)
    vaga.lacunas = skills.rotulos(citadas - da_candidata)
    vaga.experiencia_exigida = experiencia_exigida(texto)
    vaga.score = calcular_score(vaga, perfil, citadas_expandidas)
    return vaga


def calcular_score(vaga: Vaga, perfil: Perfil, skills_vaga: set[str] | None = None) -> int:
    if skills_vaga is None:
        skills_vaga = skills.expandir(skills.detectar(f"{vaga.titulo}\n{vaga.descricao}"))
    titulo = normalizar(vaga.titulo)
    cidade = _cidade(vaga.local)

    score = 0

    # Skills
    score += _pontuar_skills(perfil.skills_principais, skills_vaga,
                             config.PONTOS_SKILL_PRINCIPAL, config.MAX_SKILL_PRINCIPAL)
    score += _pontuar_skills(perfil.skills_secundarias, skills_vaga,
                             config.PONTOS_SKILL_SECUNDARIA, config.MAX_SKILL_SECUNDARIA)

    # Localização
    if cidade and cidade in {normalizar(c) for c in perfil.cidades_presencial}:
        score += config.PONTOS_CIDADE_PRESENCIAL

    # Modalidade
    if (vaga.modalidade == "remoto" and perfil.aceita_remoto) or (
        vaga.modalidade == "hibrido" and cidade in {normalizar(c) for c in perfil.cidades_hibrido}
    ):
        score += config.PONTOS_MODALIDADE

    # Senioridade: bônus se cita nível aceito OU não cita nível nenhum.
    niveis = niveis_no_titulo(vaga.titulo)
    cita_outro_cargo = _casa_algum(PADROES_OUTRAS_SENIORIDADES, titulo)
    if (niveis & set(perfil.niveis_aceitos)) or (not niveis and not cita_outro_cargo):
        score += config.PONTOS_SENIORIDADE

    # Experiência exigida muito acima da do perfil.
    exigida = vaga.experiencia_exigida
    if exigida is not None and perfil.anos_experiencia is not None:
        excesso = exigida - perfil.anos_experiencia - config.EXPERIENCIA_TOLERANCIA
        if excesso > 0:
            # math.ceil arredonda para cima: excesso 1 ou 2 -> 1 faixa; 3 ou 4 -> 2 faixas.
            penalidade = config.PENALIDADE_EXPERIENCIA * math.ceil(excesso / 2)
            score -= min(penalidade, config.MAX_PENALIDADE_EXPERIENCIA)

    # Descarte (-100): limitamos a 100 ANTES de subtrair, então uma vaga
    # descartada sempre termina em 0, mesmo que tenha somado 110 pontos.
    score = min(100, score)
    if deve_descartar(vaga.titulo, perfil):
        score -= 100

    return max(0, score)


def aprovada(vaga: Vaga, perfil: Perfil) -> bool:
    """True se a vaga deve entrar no painel."""
    return not deve_descartar(vaga.titulo, perfil) and vaga.score >= config.SCORE_MINIMO
