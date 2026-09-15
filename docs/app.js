/* Radar de Vagas TI — painel estático (Vue 3 via CDN, sem build). */

const { createApp, ref, reactive, computed, watch, onMounted } = Vue;

const CHAVE_STATUS = "radar-vagas:status";   // { [idDaVaga]: "interessante" | "aplicada" | "descartada" }
const CHAVE_FILTROS = "radar-vagas:filtros";
const TAMANHO_PAGINA = 40;

const MODALIDADES = {
  remoto: "Remoto",
  hibrido: "Híbrido",
  presencial: "Presencial",
  indefinido: "Não informado",
};

const STATUS = [
  { valor: "nova", rotulo: "Nova", icone: "🆕" },
  { valor: "interessante", rotulo: "Interessante", icone: "⭐" },
  { valor: "aplicada", rotulo: "Aplicada", icone: "✅" },
  { valor: "descartada", rotulo: "Descartada", icone: "🚫" },
];

const ABAS = [
  { valor: "todas", rotulo: "Todas" },
  { valor: "nova", rotulo: "Novas" },
  { valor: "interessante", rotulo: "Interessantes" },
  { valor: "aplicada", rotulo: "Aplicadas" },
  { valor: "descartada", rotulo: "Descartadas" },
];

const FILTROS_PADRAO = {
  status: "todas",
  texto: "",
  modalidade: "",
  fonte: "",
  scoreMinimo: 0,
  ocultarExpiradas: true,
  maxLacunas: "",
  ordem: "score",
};

/* localStorage pode falhar (aba anônima, armazenamento cheio/bloqueado). */
function lerStorage(chave, padrao) {
  try {
    const bruto = localStorage.getItem(chave);
    return bruto ? JSON.parse(bruto) : padrao;
  } catch {
    return padrao;
  }
}

function gravarStorage(chave, valor) {
  try {
    localStorage.setItem(chave, JSON.stringify(valor));
    return true;
  } catch {
    return false;
  }
}

/* Busca sem acento e sem diferenciar maiúsculas. */
function normalizar(texto) {
  return (texto || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

createApp({
  setup() {
    const vagas = ref([]);
    const atualizadoEm = ref(null);
    const carregando = ref(true);
    const erro = ref("");
    const status = reactive(lerStorage(CHAVE_STATUS, {}));
    const filtros = reactive({ ...FILTROS_PADRAO, ...lerStorage(CHAVE_FILTROS, {}) });
    const expandidas = reactive({});
    const filtrosAbertos = ref(false);
    const menuAberto = ref(false);
    const mensagemMenu = ref("");
    const limite = ref(TAMANHO_PAGINA);

    // ------------------------------------------------------------------
    // Carga dos dados
    // ------------------------------------------------------------------
    async function carregar() {
      try {
        // ?t= evita cache antigo do GitHub Pages/navegador.
        const resposta = await fetch(`data/vagas.json?t=${Date.now()}`);
        if (!resposta.ok) throw new Error(`HTTP ${resposta.status}`);
        const dados = await resposta.json();
        vagas.value = Array.isArray(dados) ? dados : dados.vagas || [];
        atualizadoEm.value = dados.atualizado_em || null;
      } catch (e) {
        erro.value = `Não foi possível carregar as vagas (${e.message}).`;
      } finally {
        carregando.value = false;
      }
    }
    onMounted(carregar);

    // ------------------------------------------------------------------
    // Status por vaga
    // ------------------------------------------------------------------
    const statusDe = (id) => status[id] || "nova";

    function definirStatus(id, valor) {
      if (valor === "nova") delete status[id];
      else status[id] = valor;
    }

    watch(status, () => gravarStorage(CHAVE_STATUS, status), { deep: true });
    watch(filtros, () => gravarStorage(CHAVE_FILTROS, filtros), { deep: true });

    // Ao mudar qualquer filtro, volta para a primeira "página".
    watch(filtros, () => { limite.value = TAMANHO_PAGINA; }, { deep: true });

    // ------------------------------------------------------------------
    // Filtros
    // ------------------------------------------------------------------
    const fontes = computed(() => [...new Set(vagas.value.map((v) => v.fonte))].sort());

    // Todos os filtros, exceto o de status (usado para os contadores das abas).
    const vagasSemFiltroStatus = computed(() => {
      const termo = normalizar(filtros.texto);
      return vagas.value.filter((v) => {
        if (filtros.ocultarExpiradas && v.expirada) return false;
        if (filtros.modalidade && v.modalidade !== filtros.modalidade) return false;
        if (filtros.fonte && v.fonte !== filtros.fonte) return false;
        if (v.score < filtros.scoreMinimo) return false;
        if (filtros.maxLacunas !== "" && (v.lacunas || []).length > Number(filtros.maxLacunas)) return false;
        if (termo) {
          const skills = [...(v.skills_match || []), ...(v.lacunas || [])].join(" ");
          const alvo = normalizar(`${v.titulo} ${v.empresa} ${v.local} ${skills} ${v.descricao}`);
          if (!alvo.includes(termo)) return false;
        }
        return true;
      });
    });

    const contadores = computed(() => {
      const c = { todas: 0, nova: 0, interessante: 0, aplicada: 0, descartada: 0 };
      for (const v of vagasSemFiltroStatus.value) {
        const s = statusDe(v.id);
        c[s] += 1;
        if (s !== "descartada") c.todas += 1;
      }
      return c;
    });

    const vagasFiltradas = computed(() => {
      const lista = vagasSemFiltroStatus.value.filter((v) => {
        const s = statusDe(v.id);
        // "Todas" esconde as descartadas; elas só aparecem na aba própria.
        return filtros.status === "todas" ? s !== "descartada" : s === filtros.status;
      });
      if (filtros.ordem === "compatibilidade") {
        // Sem skills identificadas vai para o fim; empate desempata pelo score.
        return [...lista].sort((a, b) =>
          (compatibilidade(b) ?? -1) - (compatibilidade(a) ?? -1) || b.score - a.score);
      }
      if (filtros.ordem === "data") {
        return [...lista].sort((a, b) =>
          (b.data_publicacao || b.data_coleta || "").localeCompare(a.data_publicacao || a.data_coleta || ""));
      }
      return lista; // o JSON já vem ordenado por score
    });

    const vagasVisiveis = computed(() => vagasFiltradas.value.slice(0, limite.value));

    const filtrosAtivos = computed(() =>
      ["modalidade", "fonte", "scoreMinimo", "maxLacunas"].filter((k) => filtros[k] !== FILTROS_PADRAO[k]).length
      + (filtros.ocultarExpiradas !== FILTROS_PADRAO.ocultarExpiradas ? 1 : 0)
      + (filtros.ordem !== FILTROS_PADRAO.ordem ? 1 : 0));

    function limparFiltros() {
      Object.assign(filtros, { ...FILTROS_PADRAO, status: filtros.status });
    }

    // ------------------------------------------------------------------
    // Export / Import do status
    // ------------------------------------------------------------------
    function exportarStatus() {
      const conteudo = {
        app: "radar-vagas",
        versao: 1,
        exportado_em: new Date().toISOString(),
        status: { ...status },
      };
      const blob = new Blob([JSON.stringify(conteudo, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `radar-vagas-status-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      mensagemMenu.value = `${Object.keys(status).length} status exportados.`;
    }

    async function importarStatus(evento) {
      const arquivo = evento.target.files[0];
      evento.target.value = ""; // permite importar o mesmo arquivo de novo
      if (!arquivo) return;
      try {
        const dados = JSON.parse(await arquivo.text());
        const recebidos = dados.status || dados;
        const validos = STATUS.map((s) => s.valor);
        let total = 0;
        for (const [id, valor] of Object.entries(recebidos)) {
          if (!validos.includes(valor)) continue;
          definirStatus(id, valor);
          total += 1;
        }
        mensagemMenu.value = `${total} status importados.`;
      } catch {
        mensagemMenu.value = "Arquivo inválido. Use um JSON exportado por este painel.";
      }
    }

    // ------------------------------------------------------------------
    // Formatação
    // ------------------------------------------------------------------
    const rtf = new Intl.RelativeTimeFormat("pt-BR", { numeric: "auto" });

    function formatarRelativo(iso) {
      const data = new Date(iso);
      if (Number.isNaN(data.getTime())) return "";
      const segundos = (data.getTime() - Date.now()) / 1000;
      const escalas = [
        ["year", 31536000], ["month", 2592000], ["week", 604800],
        ["day", 86400], ["hour", 3600], ["minute", 60],
      ];
      for (const [unidade, s] of escalas) {
        if (Math.abs(segundos) >= s) return rtf.format(Math.round(segundos / s), unidade);
      }
      return "agora";
    }

    function formatarDataHora(iso) {
      const data = new Date(iso);
      if (Number.isNaN(data.getTime())) return "";
      return data.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
    }

    /* % das skills citadas na vaga que estão no currículo (null se a vaga não cita nenhuma). */
    function compatibilidade(vaga) {
      const ok = (vaga.skills_match || []).length;
      const total = ok + (vaga.lacunas || []).length;
      return total ? Math.round((ok / total) * 100) : null;
    }

    function classeScore(score) {
      if (score >= 70) return "score--alto";
      if (score >= 50) return "score--medio";
      return "score--baixo";
    }

    return {
      // constantes
      MODALIDADES, STATUS, TAMANHO_PAGINA, abas: ABAS,
      // estado
      vagas, atualizadoEm, carregando, erro, filtros, expandidas,
      filtrosAbertos, menuAberto, mensagemMenu, limite,
      // derivados
      fontes, contadores, vagasFiltradas, vagasVisiveis, filtrosAtivos,
      // ações
      statusDe, definirStatus, limparFiltros, exportarStatus, importarStatus,
      formatarRelativo, formatarDataHora, classeScore, compatibilidade,
    };
  },
}).mount("#app");
