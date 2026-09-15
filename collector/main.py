"""
Ponto de entrada do coletor.

Rodar a partir da raiz do projeto:
    python -m collector.main

O `-m` executa o módulo como parte do pacote `collector`, o que faz os
imports `from collector import ...` funcionarem.
"""

import logging
import sys
import time

from collector import config, storage
from collector import perfil as perfil_mod
from collector.models import Vaga
from collector.perfil import Perfil
from collector.scoring import analisar, aprovada
from collector.sources import TODAS_AS_FONTES

log = logging.getLogger("collector")


def configurar_log() -> None:
    """Log em formato chave=valor, fácil de ler e de filtrar com grep."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s level=%(levelname)s logger=%(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stdout,
    )
    # A biblioteca urllib3 (usada pelo requests) é verbosa demais em INFO.
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def coletar(perfil: Perfil) -> tuple[list[Vaga], dict[str, dict]]:
    """Executa todas as fontes ativas. Retorna (vagas aprovadas, estatísticas)."""
    aprovadas: list[Vaga] = []
    estatisticas: dict[str, dict] = {}

    for classe_fonte in TODAS_AS_FONTES:
        nome = classe_fonte.nome
        if not config.FONTES_ATIVAS.get(nome, False):
            log.info("fonte_desativada fonte=%s", nome)
            continue

        fonte = classe_fonte(perfil)
        if not fonte.disponivel():
            estatisticas[nome] = {"status": "pulada"}
            continue

        inicio = time.monotonic()
        try:
            brutas = fonte.fetch()
        except Exception:  # noqa: BLE001
            # Qualquer erro inesperado na fonte: registra e segue com as demais.
            log.exception("fonte_falhou fonte=%s", nome)
            estatisticas[nome] = {"status": "erro"}
            continue

        for vaga in brutas:
            analisar(vaga, perfil)
        ok = [v for v in brutas if aprovada(v, perfil)]
        aprovadas.extend(ok)

        estatisticas[nome] = {
            "status": "ok",
            "brutas": len(brutas),
            "aprovadas": len(ok),
            "segundos": round(time.monotonic() - inicio, 1),
        }
        log.info("fonte_concluida fonte=%s brutas=%d aprovadas=%d segundos=%.1f",
                 nome, len(brutas), len(ok), estatisticas[nome]["segundos"])

    return aprovadas, estatisticas


def main() -> int:
    configurar_log()
    log.info("coleta_iniciada arquivo=%s", config.ARQUIVO_VAGAS)

    perfil = perfil_mod.carregar(config.ARQUIVO_PERFIL)
    existentes = storage.carregar(config.ARQUIVO_VAGAS)
    # Reanalisa as vagas já conhecidas: se o perfil mudou, score e
    # "combina/falta" ficam coerentes também nas vagas antigas.
    for vaga in existentes:
        analisar(vaga, perfil)

    novas, estatisticas = coletar(perfil)

    # Proteção: se TODAS as fontes falharam, não mexe no arquivo.
    # Sem isso, uma queda geral de rede faria as vagas "envelhecerem" à toa.
    if not any(e.get("status") == "ok" for e in estatisticas.values()):
        log.error("nenhuma_fonte_ok estatisticas=%s", estatisticas)
        return 1

    ids_existentes = {v.id for v in existentes}
    final = storage.mesclar(existentes, novas)
    alterou = storage.salvar(config.ARQUIVO_VAGAS, final)

    log.info(
        "coleta_finalizada total=%d novas=%d ativas=%d expiradas=%d arquivo_alterado=%s",
        len(final),
        len({v.id for v in novas} - ids_existentes),
        sum(1 for v in final if not v.expirada),
        sum(1 for v in final if v.expirada),
        alterou,
    )
    return 0


# Este bloco só roda quando o arquivo é executado diretamente
# (python -m collector.main), e não quando é importado por outro módulo.
if __name__ == "__main__":
    sys.exit(main())
