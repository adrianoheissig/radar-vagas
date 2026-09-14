"""
Leitura, mesclagem (deduplicação + histórico) e gravação do vagas.json.

Formato do arquivo:
{
  "atualizado_em": "2026-09-14T19:30:00Z",   <- última vez que a lista MUDOU
  "total": 42,
  "vagas": [ {...}, {...} ]
}

Idempotência: se a coleta não trouxer nada novo, o arquivo não é
reescrito — por isso `ultima_vista` guarda só a DATA (e não hora), e
`atualizado_em` só muda quando a lista de vagas muda. Assim o workflow
não gera commits vazios a cada execução.
"""

import json
import logging
from datetime import date
from pathlib import Path

from collector import config
from collector.models import Vaga
from collector.utils import agora_utc, formatar_iso

log = logging.getLogger(__name__)


def carregar(caminho: Path) -> list[Vaga]:
    """Lê as vagas do JSON existente. Retorna lista vazia se não houver arquivo."""
    if not caminho.exists():
        log.info("arquivo_inexistente caminho=%s", caminho)
        return []
    try:
        # `with` garante que o arquivo é fechado, mesmo se der erro.
        with caminho.open(encoding="utf-8") as f:
            dados = json.load(f)
    except (OSError, json.JSONDecodeError):
        log.exception("falha_ao_ler_json caminho=%s", caminho)
        return []

    vagas = []
    for item in dados.get("vagas", []):
        try:
            vagas.append(Vaga.de_dict(item))
        except (TypeError, ValueError) as erro:
            log.warning("vaga_invalida_ignorada erro=%s", erro)
    return vagas


def mesclar(existentes: list[Vaga], novas: list[Vaga], hoje: date | None = None) -> list[Vaga]:
    """Junta vagas já conhecidas com as recém-coletadas.

    Regras:
    - Mesmo id (título+empresa) = mesma vaga. Nunca duplica.
    - Se a mesma vaga veio de mais de uma fonte nesta coleta, fica a de maior score.
    - Vaga já conhecida mantém a `data_coleta` original.
    - Toda vaga vista hoje recebe `ultima_vista = hoje` e deixa de ser expirada.
    - Vaga não vista há mais de DIAS_PARA_EXPIRAR dias -> `expirada = True`.
    - Vaga não vista há mais de DIAS_PARA_REMOVER dias -> sai do arquivo.

    `hoje` é parâmetro para os testes conseguirem simular datas.
    """
    hoje = hoje or agora_utc().date()

    # Dict comprehension: {chave: valor for item in lista}
    por_id: dict[str, Vaga] = {v.id: v for v in existentes}

    # 1) Deduplica dentro da própria coleta.
    unicas: dict[str, Vaga] = {}
    for vaga in novas:
        atual = unicas.get(vaga.id)
        if atual is None or vaga.score > atual.score:
            unicas[vaga.id] = vaga

    # 2) Aplica sobre o histórico.
    for vaga_id, nova in unicas.items():
        antiga = por_id.get(vaga_id)
        if antiga is not None:
            nova.data_coleta = antiga.data_coleta
            # Algumas fontes não informam a data; aproveita a que já tínhamos.
            nova.data_publicacao = nova.data_publicacao or antiga.data_publicacao
        nova.ultima_vista = hoje.isoformat()
        nova.expirada = False
        por_id[vaga_id] = nova

    # 3) Recalcula expiração e remove as muito antigas.
    resultado = []
    for vaga in por_id.values():
        dias_sem_ver = (hoje - date.fromisoformat(vaga.ultima_vista)).days
        if config.DIAS_PARA_REMOVER and dias_sem_ver > config.DIAS_PARA_REMOVER:
            continue
        vaga.expirada = dias_sem_ver > config.DIAS_PARA_EXPIRAR
        resultado.append(vaga)

    return ordenar(resultado)


def ordenar(vagas: list[Vaga]) -> list[Vaga]:
    """Ordena por score desc e, em caso de empate, data_publicacao desc.

    Truque: o sort do Python é *estável* (mantém a ordem relativa de itens
    empatados). Então ordenamos primeiro pelo critério secundário e depois
    pelo principal. Datas ISO podem ser comparadas como string.
    """
    vagas = sorted(vagas, key=lambda v: v.data_publicacao or "", reverse=True)
    return sorted(vagas, key=lambda v: v.score, reverse=True)


def salvar(caminho: Path, vagas: list[Vaga]) -> bool:
    """Grava o JSON somente se a lista de vagas mudou. Retorna True se gravou."""
    lista_nova = [v.para_dict() for v in vagas]

    if caminho.exists():
        try:
            with caminho.open(encoding="utf-8") as f:
                if json.load(f).get("vagas") == lista_nova:
                    log.info("sem_mudancas arquivo=%s", caminho)
                    return False
        except (OSError, json.JSONDecodeError):
            pass  # arquivo corrompido: sobrescreve

    dados = {
        "atualizado_em": formatar_iso(agora_utc()),
        "total": len(lista_nova),
        "vagas": lista_nova,
    }
    caminho.parent.mkdir(parents=True, exist_ok=True)

    # Grava num arquivo temporário e renomeia: se o processo morrer no meio,
    # o vagas.json antigo continua íntegro.
    temporario = caminho.with_suffix(".tmp")
    with temporario.open("w", encoding="utf-8") as f:
        # ensure_ascii=False mantém "São Paulo" legível em vez de "São".
        json.dump(dados, f, ensure_ascii=False, indent=2)
        f.write("\n")
    temporario.replace(caminho)

    log.info("arquivo_gravado caminho=%s total=%d", caminho, len(lista_nova))
    return True
