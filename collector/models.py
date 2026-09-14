"""
Modelo de dados da vaga.

@dataclass gera automaticamente __init__, __repr__ e __eq__ a partir dos
campos declarados — parecido com um "record" do Java ou uma interface
TypeScript que já vem com construtor.
"""

import hashlib
from dataclasses import asdict, dataclass, field, fields

from collector import config
from collector.utils import (
    agora_utc,
    formatar_iso,
    limpar_espacos,
    normalizar,
    truncar,
)

MODALIDADES = ("presencial", "hibrido", "remoto", "indefinido")


def gerar_id(titulo: str, empresa: str, local: str = "") -> str:
    """SHA1 de titulo+empresa normalizados — a mesma vaga gera o mesmo id.

    Normalizar antes do hash faz 'Dev Front-End Jr' e 'dev front end jr'
    virarem o mesmo id, mesmo vindo de fontes diferentes.

    Quando a empresa não é informada (acontece na Adzuna), incluímos o local
    no hash para não fundir vagas diferentes de empresas "anônimas".
    """
    empresa_norm = normalizar(empresa)
    chave = f"{normalizar(titulo)}|{empresa_norm}"
    if not empresa_norm:
        chave += f"|{normalizar(local)}"
    # .encode() transforma str em bytes, que é o que o hashlib espera.
    return hashlib.sha1(chave.encode("utf-8")).hexdigest()


# kw_only=True obriga a criar a vaga com argumentos nomeados:
#   Vaga(titulo="...", empresa="...")   <- ok
#   Vaga("...", "...")                  <- erro
# Isso evita trocar a ordem dos campos sem perceber.
@dataclass(kw_only=True)
class Vaga:
    titulo: str
    empresa: str
    url: str
    fonte: str
    local: str = ""
    modalidade: str = "indefinido"
    data_publicacao: str | None = None
    descricao: str = ""
    score: int = 0
    # field(default_factory=...) chama a função a cada nova instância.
    # Se usássemos `= formatar_iso(agora_utc())` direto, o valor seria
    # calculado UMA vez só, quando o módulo fosse importado.
    data_coleta: str = field(default_factory=lambda: formatar_iso(agora_utc()))
    ultima_vista: str = field(default_factory=lambda: agora_utc().date().isoformat())
    expirada: bool = False
    id: str = ""

    def __post_init__(self) -> None:
        """Roda logo após o __init__ gerado pelo dataclass."""
        self.titulo = limpar_espacos(self.titulo)
        self.empresa = limpar_espacos(self.empresa)
        self.local = limpar_espacos(self.local)
        self.url = (self.url or "").strip()

        if not self.titulo:
            raise ValueError("Vaga sem título")
        if not self.url:
            # A URL é obrigatória: o painel só serve para levar ao link oficial.
            raise ValueError(f"Vaga sem URL: {self.titulo!r}")
        if self.modalidade not in MODALIDADES:
            self.modalidade = "indefinido"
        if not self.id:
            self.id = gerar_id(self.titulo, self.empresa, self.local)

    # ------------------------------------------------------------------
    # Serialização
    # ------------------------------------------------------------------

    def para_dict(self) -> dict:
        """Converte para dict pronto para JSON (com id como primeira chave).

        A descrição é truncada só aqui, na gravação: assim o score é
        calculado sobre o texto completo que veio da fonte.
        """
        dados = asdict(self)
        dados["descricao"] = truncar(self.descricao, config.TAMANHO_MAX_DESCRICAO)
        # Dicts em Python preservam a ordem de inserção (desde a 3.7).
        return {"id": dados.pop("id"), **dados}

    # @classmethod recebe a própria classe (cls) em vez de uma instância.
    # É o jeito idiomático de criar "construtores alternativos".
    @classmethod
    def de_dict(cls, dados: dict) -> "Vaga":
        """Cria uma Vaga a partir do dict lido do JSON, ignorando chaves extras."""
        nomes_validos = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in dados.items() if k in nomes_validos})
