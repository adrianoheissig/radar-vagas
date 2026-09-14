"""
Funções utilitárias usadas por várias partes do coletor.

Dica de Python: funções "privadas" (uso interno do módulo) costumam
começar com _ (underline). Novamente, é convenção — nada impede o import.
"""

import html
import re
import unicodedata
from datetime import datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup

from collector import config

# Fuso de Brasília (UTC-3). O Brasil não tem horário de verão desde 2019.
FUSO_BRASILIA = timezone(timedelta(hours=-3))


# ---------------------------------------------------------------------------
# Texto
# ---------------------------------------------------------------------------

def remover_acentos(texto: str) -> str:
    """'Sênior Júnior' -> 'Senior Junior'.

    unicodedata.normalize("NFKD") separa a letra do acento
    (ê vira e + ^); depois descartamos os caracteres de acento ("combining").
    """
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c))


def normalizar(texto: str | None) -> str:
    """Deixa o texto comparável: minúsculo, sem acento, sem pontuação.

    Ex.: 'Desenvolvedor(a) Front-End Sr.' -> 'desenvolvedor a front end sr'

    O tipo `str | None` quer dizer "string ou None" (o null do Python).
    """
    if not texto:
        return ""
    texto = remover_acentos(texto).lower()
    # re.sub troca tudo que casar com a regex. [^a-z0-9]+ = "qualquer
    # sequência de caracteres que NÃO seja letra ou número".
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    return texto.strip()


def limpar_espacos(texto: str | None) -> str:
    """Colapsa quebras de linha e espaços repetidos em um espaço só."""
    if not texto:
        return ""
    return re.sub(r"\s+", " ", texto).strip()


def limpar_html(texto: str | None) -> str:
    """Remove tags HTML e entidades (&amp;, &#xEA; ...) de um texto."""
    if not texto:
        return ""
    # Só passa pelo BeautifulSoup se parecer HTML (é mais lento).
    if "<" in texto and ">" in texto:
        texto = BeautifulSoup(texto, "html.parser").get_text(" ")
    return limpar_espacos(html.unescape(texto))


def truncar(texto: str, limite: int) -> str:
    """Corta o texto em `limite` caracteres, adicionando '…' se cortou."""
    if len(texto) <= limite:
        return texto
    return texto[: limite - 1].rstrip() + "…"


# ---------------------------------------------------------------------------
# Modalidade
# ---------------------------------------------------------------------------

def detectar_modalidade(*textos: str | None) -> str:
    """Tenta descobrir a modalidade lendo título/descrição/local.

    *textos recebe quantos argumentos você passar, como uma tupla.
    Ex.: detectar_modalidade(titulo, descricao)

    A ordem importa: 'híbrido' é checado antes de 'remoto' porque textos de
    vagas híbridas costumam dizer coisas como "2 dias remoto".
    """
    texto = normalizar(" ".join(t for t in textos if t))
    if re.search(r"\bhibrid[oa]\b|\bhybrid\b", texto):
        return "hibrido"
    if re.search(r"\bremot[oa]\b|\bhome office\b|\bremote\b|\bteletrabalho\b", texto):
        return "remoto"
    if re.search(r"\bpresencial\b|\bon site\b", texto):
        return "presencial"
    return "indefinido"


# ---------------------------------------------------------------------------
# Datas
# ---------------------------------------------------------------------------

def agora_utc() -> datetime:
    return datetime.now(timezone.utc)


def formatar_iso(dt: datetime) -> str:
    """datetime -> '2026-09-14T19:30:00Z' (sempre em UTC)."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def para_iso_utc(valor: str | None, formato: str | None = None,
                 fuso_padrao: timezone = timezone.utc) -> str | None:
    """Converte datas em vários formatos para ISO UTC. Retorna None se falhar.

    - Sem `formato`: aceita ISO 8601 ('2026-09-10T19:58:20.510Z').
    - Com `formato`: usa strptime, ex. '%Y/%m/%d %H:%M:%S'.
    - `fuso_padrao` é usado quando a data não traz fuso.
    """
    if not valor:
        return None
    try:
        if formato:
            dt = datetime.strptime(valor.strip(), formato)
        else:
            # fromisoformat entende 'Z' a partir do Python 3.11.
            dt = datetime.fromisoformat(valor.strip())
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=fuso_padrao)
    return formatar_iso(dt)


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def criar_sessao() -> requests.Session:
    """Cria uma sessão HTTP reutilizável.

    Uma Session reaproveita a conexão TCP entre chamadas ao mesmo host
    (mais rápido) e guarda cabeçalhos padrão.
    """
    sessao = requests.Session()
    sessao.headers.update({
        "User-Agent": config.USER_AGENT,
        "Accept-Language": "pt-BR,pt;q=0.9",
    })
    return sessao
