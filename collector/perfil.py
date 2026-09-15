"""
Perfil da candidata: o que o coletor busca e como pontua.

O perfil fica em `perfil.json`, na raiz do projeto, e é gerado a partir do
currículo. Guarda SÓ dados técnicos (skills, anos, cidades aceitas): nome,
telefone e e-mail nunca são gravados. O PDF do currículo não vai para o git.

Gerar (no seu computador, uma vez):
    python -m collector.perfil gerar "/caminho/curriculo.pdf"

Depois revise o perfil.json à mão: a leitura do PDF é heurística.
Se o perfil.json não existir, o coletor usa os valores padrão do config.py.
"""

import argparse
import json
import logging
import re
import sys
from dataclasses import asdict, dataclass, field, fields
from datetime import date
from pathlib import Path

from collector import config, skills
from collector.utils import normalizar

log = logging.getLogger(__name__)

NIVEIS = ("estagio", "junior", "pleno", "senior")

UFS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA",
    "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}

AJUDA = (
    "Perfil gerado a partir do currículo. Revise à vontade. "
    "skills_*: ids de collector/skills.py (ex.: react, node, mysql). "
    "Principais valem +15 cada (máx. 45), secundárias +10 (máx. 20); "
    "skills_conhecidas servem para mostrar 'combina/falta' no painel. "
    "niveis_aceitos: estagio, junior, pleno, senior (títulos com outros níveis são descartados). "
    f"termos_busca: no máximo {config.MAX_TERMOS_BUSCA} (cota da Adzuna). "
    f"consultas_jsearch: no máximo {config.MAX_CONSULTAS_JSEARCH} (cota do JSearch)."
)


@dataclass(kw_only=True)
class Perfil:
    anos_experiencia: int | None = None
    niveis_aceitos: list[str] = field(default_factory=lambda: ["junior", "pleno"])
    skills_principais: list[str] = field(default_factory=list)
    skills_secundarias: list[str] = field(default_factory=list)
    skills_conhecidas: list[str] = field(default_factory=list)
    cidades_presencial: list[str] = field(default_factory=list)
    cidades_hibrido: list[str] = field(default_factory=list)
    aceita_remoto: bool = True
    termos_busca: list[str] = field(default_factory=list)
    consultas_jsearch: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Valores derivados
    # ------------------------------------------------------------------

    def todas_as_skills(self) -> set[str]:
        """Tudo que a candidata sabe, incluindo o que está implícito."""
        explicitas = set(self.skills_principais) | set(self.skills_secundarias) | set(self.skills_conhecidas)
        return skills.expandir(explicitas)

    def localidades_busca(self) -> list[str]:
        """Cidades usadas no filtro 'where' das APIs, sem repetição."""
        vistas, resultado = set(), []
        for cidade in self.cidades_hibrido + self.cidades_presencial:
            if normalizar(cidade) not in vistas:
                vistas.add(normalizar(cidade))
                resultado.append(cidade)
        return resultado

    # ------------------------------------------------------------------
    # Criação
    # ------------------------------------------------------------------

    @classmethod
    def padrao(cls) -> "Perfil":
        """Perfil usado quando não existe perfil.json (valores do config.py)."""
        return cls(
            skills_principais=list(config.SKILLS_PRINCIPAIS),
            skills_secundarias=list(config.SKILLS_SECUNDARIAS),
            cidades_presencial=["Guarulhos"],
            cidades_hibrido=["São Paulo"],
            termos_busca=list(config.TERMOS_BUSCA),
            consultas_jsearch=list(config.JSEARCH_CONSULTAS),
        )

    @classmethod
    def de_dict(cls, dados: dict) -> "Perfil":
        nomes = {f.name for f in fields(cls)}
        perfil = cls(**{k: v for k, v in dados.items() if k in nomes})
        perfil._validar()
        return perfil

    def _validar(self) -> None:
        """Avisa sobre valores estranhos e corta o que estouraria as cotas das APIs."""
        for campo in ("skills_principais", "skills_secundarias", "skills_conhecidas"):
            desconhecidas = [s for s in getattr(self, campo) if s not in skills.POR_ID]
            if desconhecidas:
                log.warning("perfil_skill_desconhecida campo=%s ids=%s", campo, desconhecidas)
        invalidos = [n for n in self.niveis_aceitos if n not in NIVEIS]
        if invalidos:
            log.warning("perfil_nivel_desconhecido niveis=%s validos=%s", invalidos, NIVEIS)
        if len(self.termos_busca) > config.MAX_TERMOS_BUSCA:
            log.warning("perfil_termos_cortados de=%d para=%d",
                        len(self.termos_busca), config.MAX_TERMOS_BUSCA)
            self.termos_busca = self.termos_busca[: config.MAX_TERMOS_BUSCA]
        if len(self.consultas_jsearch) > config.MAX_CONSULTAS_JSEARCH:
            log.warning("perfil_consultas_jsearch_cortadas de=%d para=%d",
                        len(self.consultas_jsearch), config.MAX_CONSULTAS_JSEARCH)
            self.consultas_jsearch = self.consultas_jsearch[: config.MAX_CONSULTAS_JSEARCH]
        if not self.termos_busca:
            self.termos_busca = list(config.TERMOS_BUSCA)


# ---------------------------------------------------------------------------
# Arquivo
# ---------------------------------------------------------------------------

def carregar(caminho: Path = config.ARQUIVO_PERFIL) -> Perfil:
    if not caminho.exists():
        log.warning("perfil_inexistente caminho=%s usando=config.py", caminho)
        return Perfil.padrao()
    with caminho.open(encoding="utf-8") as f:
        perfil = Perfil.de_dict(json.load(f))
    log.info("perfil_carregado principais=%s secundarias=%s anos=%s niveis=%s termos=%d",
             perfil.skills_principais, perfil.skills_secundarias,
             perfil.anos_experiencia, perfil.niveis_aceitos, len(perfil.termos_busca))
    return perfil


def salvar(perfil: Perfil, caminho: Path) -> None:
    dados = {"_leia_me": AJUDA, **asdict(perfil)}
    with caminho.open("w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
        f.write("\n")


# ---------------------------------------------------------------------------
# Leitura do currículo
# ---------------------------------------------------------------------------

def extrair_texto(caminho: Path) -> str:
    """Extrai o texto de um PDF (ou lê um .txt/.md)."""
    if caminho.suffix.lower() != ".pdf":
        return caminho.read_text(encoding="utf-8")
    try:
        # Import aqui dentro: pypdf só é necessário para gerar o perfil,
        # não para rodar a coleta no GitHub Actions.
        from pypdf import PdfReader
    except ImportError:
        sys.exit("Instale o pypdf para ler PDF:  pip install -r requirements-dev.txt")
    leitor = PdfReader(str(caminho))
    return "\n".join(pagina.extract_text() or "" for pagina in leitor.pages)


def _eh_titulo(linha: str) -> bool:
    """Títulos de seção de currículo costumam vir em MAIÚSCULAS: 'EXPERIÊNCIA:'."""
    linha = linha.strip().rstrip(":")
    return len(linha) >= 5 and linha.isupper()


def secao(texto: str, nome: str) -> str:
    """Texto de uma seção, do título que começa com `nome` até o próximo título.

    Ex.: secao(texto, "resumo") pega de 'RESUMO PROFISSIONAL' até 'EXPERIÊNCIA:'.
    Retorna "" se a seção não for encontrada.
    """
    linhas, dentro = [], False
    for linha in texto.splitlines():
        if _eh_titulo(linha):
            if dentro:
                break
            dentro = normalizar(linha).startswith(nome)
            continue
        if dentro:
            linhas.append(linha)
    return "\n".join(linhas)


def detectar_anos(texto: str, hoje: date | None = None) -> int | None:
    """Anos de experiência: frase explícita ou, na falta dela, períodos de datas."""
    norm = normalizar(texto)
    explicito = re.search(r"(\d{1,2}) anos? de experiencia", norm)
    if explicito:
        return int(explicito.group(1))

    # Períodos como "2023 - 2025" ou "2025 - Atualmente" dentro da seção de experiência.
    # (?<!\d) em vez de \b porque o PDF às vezes cola o ano no nome da empresa.
    trecho = normalizar(secao(texto, "experiencia")) or norm
    ano_atual = (hoje or date.today()).year
    inicios, fins = [], []
    for inicio, fim in re.findall(
        r"(?<!\d)((?:19|20)\d{2}) (?:a |ate )?((?:19|20)\d{2}|atualmente|atual|presente|hoje)", trecho
    ):
        inicios.append(int(inicio))
        fins.append(int(fim) if fim.isdigit() else ano_atual)
    if inicios:
        return max(0, max(fins) - min(inicios))
    return None


def detectar_cidade(texto: str) -> tuple[str, str] | None:
    """Primeira ocorrência de 'Cidade, UF' ou 'Cidade - UF'. Ex.: ('Guarulhos', 'SP')"""
    padrao = r"([A-ZÀ-Ú][a-zà-ú]+(?: (?:d[aeo]s? )?[A-ZÀ-Ú][a-zà-ú]+)*)\s*[,-]\s*([A-Z]{2})\b"
    for cidade, uf in re.findall(padrao, texto):
        if uf in UFS:
            return cidade, uf
    return None


def niveis_por_anos(anos: int | None) -> list[str]:
    if anos is None:
        return ["junior", "pleno"]
    if anos < 2:
        return ["junior"]
    if anos <= 5:
        return ["junior", "pleno"]
    return ["pleno", "senior"]


def gerar_de_texto(texto: str, hoje: date | None = None) -> Perfil:
    """Monta um Perfil a partir do texto do currículo (sem dados pessoais)."""
    norm = skills.preparar_texto(texto)
    encontradas = skills.detectar(norm, ja_preparado=True)

    # Principais: skills (não comuns) citadas no resumo profissional, na ordem
    # em que aparecem — é onde a pessoa destaca a stack principal.
    resumo = skills.preparar_texto(secao(texto, "resumo")) or norm[:800]
    posicoes = {}
    for skill_id in encontradas:
        if skills.eh_comum(skill_id):
            continue
        for padrao in skills.POR_ID[skill_id].padroes:
            m = re.search(padrao, resumo)
            if m:
                posicoes[skill_id] = min(posicoes.get(skill_id, 10**9), m.start())
    principais = sorted(posicoes, key=posicoes.get)[:4]
    secundarias = [s for s in skills.ordenar(encontradas)
                   if s not in principais and not skills.eh_comum(s)]

    anos = detectar_anos(texto, hoje)
    local = detectar_cidade(texto)
    cidades_presencial = [local[0]] if local else []
    if local and local[1] == "SP":
        cidades_hibrido = ["São Paulo"]
    else:
        cidades_hibrido = list(cidades_presencial)

    # Termos de busca: cargos citados + skills principais.
    termos = []
    for chave, termo in (("full stack", "desenvolvedor fullstack"), ("fullstack", "desenvolvedor fullstack"),
                         ("frontend", "desenvolvedor frontend"), ("front end", "desenvolvedor frontend"),
                         ("backend", "desenvolvedor backend"), ("back end", "desenvolvedor backend")):
        if chave in resumo and termo not in termos:
            termos.append(termo)
    for skill_id in principais:
        termos.append(skills.POR_ID[skill_id].rotulo.lower())
    termos = termos[: config.MAX_TERMOS_BUSCA]

    cidade_busca = (cidades_hibrido or ["Brasil"])[0]
    stack = " ".join(skills.POR_ID[s].rotulo.lower() for s in principais[:2])
    cargo = termos[0] if termos else "desenvolvedor"
    nivel = niveis_por_anos(anos)[0].replace("junior", "júnior")
    consultas = [" ".join(f"{cargo} {stack} em {cidade_busca}".split()), f"{cargo} {nivel} remoto Brasil"]

    return Perfil(
        anos_experiencia=anos,
        niveis_aceitos=niveis_por_anos(anos),
        skills_principais=principais,
        skills_secundarias=secundarias,
        skills_conhecidas=skills.ordenar(encontradas),
        cidades_presencial=cidades_presencial,
        cidades_hibrido=cidades_hibrido,
        aceita_remoto=True,
        termos_busca=termos,
        consultas_jsearch=consultas[: config.MAX_CONSULTAS_JSEARCH],
    )


# ---------------------------------------------------------------------------
# Linha de comando
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gera o perfil.json a partir do currículo.")
    sub = parser.add_subparsers(dest="comando", required=True)
    gerar = sub.add_parser("gerar", help="lê o currículo (PDF) e grava o perfil.json")
    gerar.add_argument("curriculo", type=Path)
    gerar.add_argument("--saida", type=Path, default=config.ARQUIVO_PERFIL)
    gerar.add_argument("--sobrescrever", action="store_true",
                       help="substitui um perfil.json existente (perde ajustes manuais)")
    args = parser.parse_args(argv)

    if not args.curriculo.exists():
        print(f"Arquivo não encontrado: {args.curriculo}")
        return 1
    if args.saida.exists() and not args.sobrescrever:
        print(f"{args.saida} já existe. Use --sobrescrever para substituir.")
        return 1

    perfil = gerar_de_texto(extrair_texto(args.curriculo))
    salvar(perfil, args.saida)

    print(f"Perfil gravado em {args.saida}\n")
    print(f"  Anos de experiência : {perfil.anos_experiencia}")
    print(f"  Níveis aceitos      : {', '.join(perfil.niveis_aceitos)}")
    print(f"  Skills principais   : {', '.join(skills.rotulos(perfil.skills_principais))}")
    print(f"  Skills secundárias  : {', '.join(skills.rotulos(perfil.skills_secundarias))}")
    print(f"  Todas as skills     : {', '.join(skills.rotulos(perfil.skills_conhecidas))}")
    print(f"  Presencial em       : {', '.join(perfil.cidades_presencial) or '-'}")
    print(f"  Híbrido em          : {', '.join(perfil.cidades_hibrido) or '-'}")
    print(f"  Termos de busca     : {perfil.termos_busca}")
    print(f"  Consultas JSearch   : {perfil.consultas_jsearch}")
    print("\nRevise o arquivo antes de commitar — a leitura do PDF é heurística.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
