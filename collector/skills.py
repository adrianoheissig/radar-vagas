"""
Dicionário de skills: sinônimos e relações entre tecnologias.

É usado tanto para ler o currículo quanto para ler as vagas, então os dois
lados "falam a mesma língua". Exemplos do que ele resolve:

- "React.JS", "ReactJS" e "react" viram a mesma skill: react
- "JavaScript" NÃO conta como "Java"
- "Next.js" implica React (quem pede Next.js está pedindo React)
- "C#" e ".NET" não se perdem quando a pontuação é removida

Para adicionar uma tecnologia, acrescente um Skill(...) na lista SKILLS.
Os padrões são regex aplicadas sobre texto normalizado: minúsculo, sem
acento e com pontuação trocada por espaço ("Node.js" -> "node js").
"""

import re
from dataclasses import dataclass

from collector.utils import normalizar


# frozen=True torna o objeto imutável (e "hashable", pode ir em sets).
@dataclass(frozen=True)
class Skill:
    id: str                       # identificador interno, ex.: "react"
    rotulo: str                   # como aparece no painel, ex.: "React"
    padroes: tuple[str, ...]      # regex sobre texto normalizado
    # Skills muito comuns (HTML, Git...) contam para "combina/falta", mas
    # não dão pontos no score: quase toda vaga de frontend as menciona.
    comum: bool = False
    # Quem conhece esta skill conhece também estas (ex.: nextjs -> react).
    implica: tuple[str, ...] = ()


SKILLS: list[Skill] = [
    # ---------------- Frontend ----------------
    Skill("react", "React", (r"\breact(?: ?js)?\b(?! native)",), implica=("javascript",)),
    Skill("react_native", "React Native", (r"\breact native\b",), implica=("react",)),
    Skill("nextjs", "Next.js", (r"\bnext ?js\b",), implica=("react",)),
    Skill("redux", "Redux", (r"\bredux\b",), implica=("react",)),
    Skill("angular", "Angular", (r"\bangular(?: ?js)?\b",), implica=("typescript",)),
    Skill("vue", "Vue.js", (r"\bvue(?: ?js)?\b",), implica=("javascript",)),
    Skill("nuxt", "Nuxt", (r"\bnuxt(?: ?js)?\b",), implica=("vue",)),
    Skill("typescript", "TypeScript", (r"\btypescript\b",), implica=("javascript",)),
    Skill("javascript", "JavaScript", (r"\bjavascript\b", r"\becmascript\b", r"\bes6\b")),
    Skill("html", "HTML", (r"\bhtml ?5?\b",), comum=True),
    Skill("css", "CSS", (r"\bcss ?3?\b",), comum=True),
    Skill("sass", "Sass", (r"\bs[ac]ss\b",), implica=("css",)),
    Skill("tailwind", "Tailwind", (r"\btailwind(?: ?css)?\b",), implica=("css",)),
    Skill("bootstrap", "Bootstrap", (r"\bbootstrap\b",), implica=("css",)),
    Skill("jquery", "jQuery", (r"\bjquery\b",), implica=("javascript",)),
    Skill("figma", "Figma", (r"\bfigma\b",)),

    # ---------------- Backend ----------------
    Skill("node", "Node.js", (r"\bnode(?: ?js)?\b",), implica=("javascript",)),
    Skill("express", "Express", (r"\bexpress(?: ?js)?\b",), implica=("node",)),
    Skill("nestjs", "NestJS", (r"\bnest ?js\b",), implica=("node", "typescript")),
    Skill("java", "Java", (r"\bjava\b(?! script)",)),
    Skill("spring", "Spring", (r"\bspring(?: boot)?\b",), implica=("java",)),
    Skill("kotlin", "Kotlin", (r"\bkotlin\b",)),
    Skill("python", "Python", (r"\bpython\b",)),
    Skill("django", "Django", (r"\bdjango\b",), implica=("python",)),
    Skill("php", "PHP", (r"\bphp\b",)),
    Skill("laravel", "Laravel", (r"\blaravel\b",), implica=("php",)),
    Skill("csharp", "C#", (r"\bcsharp\b",)),
    Skill("dotnet", ".NET", (r"\bdotnet\b", r"\basp ?net\b")),
    Skill("golang", "Go", (r"\bgolang\b",)),
    Skill("ruby", "Ruby", (r"\bruby\b", r"\brails\b")),
    Skill("rest", "APIs REST", (r"\brest(?:ful)?\b",), comum=True),
    Skill("graphql", "GraphQL", (r"\bgraphql\b",)),
    Skill("microsservicos", "Microsserviços", (r"\bmicro ?s?servicos\b", r"\bmicroservices?\b"), comum=True),

    # ---------------- Bancos de dados ----------------
    Skill("sql", "SQL", (r"\bsql\b(?! server)",), comum=True),
    Skill("mysql", "MySQL", (r"\bmysql\b",), implica=("sql",)),
    Skill("postgresql", "PostgreSQL", (r"\bpostgres(?:ql)?\b",), implica=("sql",)),
    Skill("oracle", "Oracle", (r"\boracle\b", r"\bpl sql\b"), implica=("sql",)),
    Skill("sqlserver", "SQL Server", (r"\bsql server\b",), implica=("sql",)),
    Skill("mongodb", "MongoDB", (r"\bmongo(?:db)?\b",)),
    Skill("redis", "Redis", (r"\bredis\b",)),
    Skill("firebase", "Firebase", (r"\bfirebase\b",)),

    # ---------------- Infra / DevOps ----------------
    Skill("docker", "Docker", (r"\bdocker\b",)),
    Skill("kubernetes", "Kubernetes", (r"\bkubernetes\b", r"\bk8s\b")),
    Skill("aws", "AWS", (r"\baws\b", r"\bamazon web services\b")),
    Skill("azure", "Azure", (r"\bazure\b",)),
    Skill("gcp", "Google Cloud", (r"\bgcp\b", r"\bgoogle cloud\b")),
    Skill("cicd", "CI/CD", (r"\bci cd\b", r"\bjenkins\b", r"\bgithub actions\b", r"\bgitlab ci\b")),
    Skill("linux", "Linux", (r"\blinux\b",)),

    # ---------------- Práticas / ferramentas ----------------
    Skill("git", "Git", (r"\bgit\b", r"\bgithub\b", r"\bgitlab\b", r"\bbitbucket\b"), comum=True),
    Skill("testes", "Testes automatizados", (r"\bjest\b", r"\bcypress\b", r"\bjunit\b", r"\btdd\b",
                                             r"\btestes? (?:unitarios?|automatizados?)\b")),
    Skill("agil", "Metodologias ágeis", (r"\bscrum\b", r"\bkanban\b", r"\bageis\b", r"\bagil\b"), comum=True),
    Skill("clean_code", "Clean Code", (r"\bclean code\b", r"\bsolid\b"), comum=True),
    Skill("ingles", "Inglês", (r"\bingles\b", r"\benglish\b")),
]

# Índices auxiliares, calculados uma vez só na importação do módulo.
POR_ID: dict[str, Skill] = {s.id: s for s in SKILLS}
ORDEM: dict[str, int] = {s.id: i for i, s in enumerate(SKILLS)}

# Símbolos que a normalização apagaria e que mudam o sentido.
_SUBSTITUICOES = [
    (re.compile(r"\bc ?#"), " csharp "),
    (re.compile(r"\.net\b"), " dotnet "),
    (re.compile(r"\bci ?/ ?cd\b"), " ci cd "),
]


def preparar_texto(texto: str | None) -> str:
    """Normaliza o texto preservando símbolos como C# e .NET."""
    texto = (texto or "").lower()
    for padrao, troca in _SUBSTITUICOES:
        texto = padrao.sub(troca, texto)
    return normalizar(texto)


def detectar(texto: str | None, ja_preparado: bool = False) -> set[str]:
    """Retorna os ids das skills citadas explicitamente no texto."""
    texto = texto if ja_preparado else preparar_texto(texto)
    return {s.id for s in SKILLS if any(re.search(p, texto) for p in s.padroes)}


def expandir(ids: set[str]) -> set[str]:
    """Acrescenta as skills implícitas (nextjs -> react -> javascript...)."""
    resultado = set(ids)
    pendentes = list(ids)
    while pendentes:  # repete até não surgir nenhuma skill nova
        skill = POR_ID.get(pendentes.pop())
        if not skill:
            continue
        for implicada in skill.implica:
            if implicada not in resultado:
                resultado.add(implicada)
                pendentes.append(implicada)
    return resultado


def ordenar(ids: set[str] | list[str]) -> list[str]:
    """Ordena na ordem do dicionário — garante saída estável (idempotência)."""
    return sorted(ids, key=lambda i: ORDEM.get(i, len(ORDEM)))


def rotulos(ids: set[str] | list[str]) -> list[str]:
    """ids -> rótulos legíveis, em ordem estável. Ex.: {"node"} -> ["Node.js"]"""
    return [POR_ID[i].rotulo if i in POR_ID else i for i in ordenar(ids)]


def eh_comum(skill_id: str) -> bool:
    skill = POR_ID.get(skill_id)
    return bool(skill and skill.comum)
