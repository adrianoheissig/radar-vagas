# 📡 Radar de Vagas TI

Busca automática de vagas de **Desenvolvedor(a) Fullstack/Frontend júnior-pleno** em várias fontes. As vagas são comparadas com um **perfil gerado a partir do currículo**: cada uma recebe um score e a lista do que **combina** e do que **falta**. Tudo aparece num painel web estático hospedado no GitHub Pages.

- **Perfil-alvo:** React, Angular, TypeScript, Node.js, Java, MySQL, Firebase, Figma · ~3 anos de experiência
- **Local:** presencial em Guarulhos, híbrido em São Paulo (capital) ou 100% remoto
- **Fontes:** Adzuna (API oficial), JSearch/RapidAPI (opcional), Gupy (API pública do portal), InfoJobs (scraping)
- **Custo:** zero. Nenhuma IA paga; a comparação com o currículo usa um dicionário de skills com sinônimos.

> O painel **só lista** as vagas e leva ao link oficial. Não existe candidatura nem login automatizado em nenhum portal.

```
radar-vagas/
├── collector/                 # Coletor em Python 3.12
│   ├── main.py                # ponto de entrada: python -m collector.main
│   ├── config.py              # pesos do score, limites de cota, fontes ativas
│   ├── perfil.py              # perfil da candidata + leitura do currículo (PDF)
│   ├── skills.py              # dicionário de skills: sinônimos e implicações
│   ├── models.py              # dataclass Vaga
│   ├── scoring.py             # score, "combina/falta" e experiência exigida
│   ├── storage.py             # deduplicação, histórico e gravação do JSON
│   ├── utils.py
│   └── sources/               # uma fonte por arquivo, todas com fetch() -> list[Vaga]
│       ├── base.py            # interface Fonte
│       ├── adzuna.py
│       ├── jsearch.py
│       ├── gupy.py
│       └── infojobs.py
├── tests/                     # pytest
├── docs/                      # painel (GitHub Pages publica esta pasta)
│   ├── index.html · app.js · styles.css
│   └── data/vagas.json        # gerado pelo coletor
├── .github/workflows/coletar.yml
├── perfil.json                # gerado do currículo (sem dados pessoais)
├── Dockerfile · docker-compose.yml · .env.example
└── requirements.txt · requirements-dev.txt
```

---

## 1. Criar as contas gratuitas e obter as keys

### Adzuna (obrigatória para a fonte Adzuna)

1. Acesse <https://developer.adzuna.com/signup> e crie a conta.
2. Depois do login, abra o **Dashboard → API Access Details**.
3. Copie o **Application ID** (`ADZUNA_APP_ID`) e a **Application Key** (`ADZUNA_APP_KEY`).

O plano gratuito permite cerca de 250 chamadas por dia. O coletor faz 15 chamadas por execução, ou 45 por dia.

> Os links da Adzuna trazem `utm_source=<APP_ID>` e ficam visíveis no `vagas.json` público. O App ID sozinho não dá acesso à API; o segredo é a **App Key**, que nunca é gravada.

### RapidAPI / JSearch (opcional)

1. Crie a conta em <https://rapidapi.com>.
2. Pesquise por **JSearch** e abra a API.
3. Em **Pricing**, assine o plano **Basic (gratuito)**.
4. Na aba **Endpoints**, copie o valor do header `X-RapidAPI-Key`. Essa é a `RAPIDAPI_KEY`.

O plano gratuito dá cerca de **200 requisições por mês**. O coletor faz 2 por execução (~180/mês). As consultas ficam em `consultas_jsearch` no `perfil.json` (máximo de 2, para não estourar a cota). Sem a key, a fonte é simplesmente pulada (aparece um aviso no log).

---

## 2. Configurar os Secrets no GitHub

No repositório: **Settings → Secrets and variables → Actions → New repository secret**.

| Nome             | Obrigatório | Valor                    |
|------------------|-------------|--------------------------|
| `ADZUNA_APP_ID`  | sim         | Application ID da Adzuna |
| `ADZUNA_APP_KEY` | sim         | Application Key da Adzuna|
| `RAPIDAPI_KEY`   | não         | X-RapidAPI-Key do JSearch|

Para testar, abra **Actions → Coletar vagas → Run workflow**. O workflow roda os testes, executa a coleta e só faz commit do `docs/data/vagas.json` se ele mudou.

Agendamento: `0 10,15,21 * * *` (UTC), ou seja, **7h, 12h e 18h em Brasília**.

> Se o repositório passar 60 dias sem nenhuma atividade, o GitHub desativa workflows agendados. Os commits automáticos do próprio coletor contam como atividade, mas se um dia o workflow parar, reative-o na aba Actions.

---

## 3. Ativar o GitHub Pages

1. **Settings → Pages**.
2. Em **Build and deployment → Source**, escolha **Deploy from a branch**.
3. Branch **`main`**, pasta **`/docs`** → **Save**.
4. Após 1 ou 2 minutos, o painel fica disponível em `https://<seu-usuario>.github.io/radar-vagas/`.

A pasta `docs/` tem um arquivo `.nojekyll` para o Pages servir os arquivos como estão, sem processar com Jekyll.

> **Privacidade:** em conta gratuita, o GitHub Pages exige repositório **público**, e o `vagas.json` fica acessível a quem tiver o link. Ele contém apenas vagas públicas, nada pessoal. O status das vagas (Interessante/Aplicada/…) fica só no `localStorage` do navegador.

### Usando o painel

- **Abas** por status, cada uma com contador: Todas (sem as descartadas), Novas, Interessantes, Aplicadas, Descartadas.
- **Cada card** mostra o que combina (verde), o que falta (vermelho), a % de compatibilidade e os anos de experiência pedidos.
- **Botões de fonte** (abaixo das abas): Todas as fontes, Adzuna, Gupy, InfoJobs, cada um com a contagem de vagas na aba atual. Um toque filtra só aquela fonte.
- **Filtros:** texto livre (inclui skills), modalidade, quanto falta (nada / até 2 / até 4 skills), score mínimo, ocultar expiradas e ordenação (score, data ou compatibilidade). Os filtros ficam salvos no navegador.
- **Menu ⋯ → Exportar/Importar status:** gera um JSON para levar seus status do computador para o celular (ou vice-versa).

---

## 4. Currículo e perfil

O coletor não lê o currículo a cada execução. Ele usa o `perfil.json`, gerado **uma vez** a partir do PDF, no seu computador:

```bash
pip install -r requirements-dev.txt
python -m collector.perfil gerar "/caminho/curriculo.pdf"
```

O comando mostra um resumo e grava o `perfil.json` na raiz do projeto. **Revise o arquivo antes de commitar**, porque a leitura do PDF é heurística. Para gerar de novo por cima de ajustes manuais, use `--sobrescrever`.

| Campo | O que controla |
|---|---|
| `anos_experiencia` | Comparado com os anos que a vaga pede (penalidade se pedir bem mais) |
| `niveis_aceitos` | `estagio`, `junior`, `pleno`, `senior`. Títulos com outros níveis são descartados |
| `skills_principais` | +15 cada no score (máx. 45). Por padrão, as citadas no resumo profissional |
| `skills_secundarias` | +10 cada (máx. 20). As demais skills técnicas do currículo |
| `skills_conhecidas` | Tudo que está no currículo. Define o que "combina" e o que "falta" |
| `cidades_presencial` | +20 se a vaga é numa dessas cidades |
| `cidades_hibrido` | +10 se a vaga é híbrida numa dessas cidades |
| `aceita_remoto` | +10 para vagas remotas; também liga as buscas por "remoto" |
| `termos_busca` | O que é pesquisado nas fontes (máx. 5, por causa da cota da Adzuna) |
| `consultas_jsearch` | Consultas do JSearch (máx. 2, por causa da cota mensal) |

Os ids de skill (`react`, `node`, `mysql`...) estão em `collector/skills.py`. Para uma tecnologia que ainda não existe no dicionário, acrescente um `Skill(...)` lá, com os sinônimos.

> **Privacidade:** o PDF **não vai para o repositório** (`*.pdf` está no `.gitignore`), e o `perfil.json` guarda só dados técnicos: skills, anos e cidades aceitas, sem nome, telefone ou e-mail. Como o repositório é público, o `perfil.json` fica visível.

Sem `perfil.json`, o coletor usa os valores padrão do `config.py`.

---

## 5. Rodar localmente

### Com Docker

```bash
cp .env.example .env        # preencha as keys
docker compose up -d painel # painel em http://localhost:8080
docker compose run --rm coletor   # roda uma coleta e atualiza docs/data/vagas.json
docker compose down
```

Se a porta 8080 estiver ocupada: `PAINEL_PORTA=8090 docker compose up -d painel`.

### Sem Docker (útil para desenvolver/testar)

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

pytest -v                              # testes
set -a; source .env; set +a            # carrega as variáveis do .env no shell
python -m collector.main               # coleta
python -m http.server 8000 -d docs     # painel em http://localhost:8000
```

> O painel precisa ser servido por HTTP. Abrir o `index.html` direto (`file://`) bloqueia o `fetch` do JSON.

---

## 6. Adicionar uma nova fonte de vagas

1. Crie `collector/sources/minha_fonte.py`:

   ```python
   from collector.models import Vaga
   from collector.sources.base import Fonte
   from collector.utils import detectar_modalidade, limpar_html, para_iso_utc


   class MinhaFonte(Fonte):
       nome = "minha_fonte"  # usado no config e no campo `fonte`

       def disponivel(self) -> bool:
           # opcional: retorne False se faltar alguma credencial
           return True

       def fetch(self) -> list[Vaga]:
           vagas = []
           for termo in self.perfil.termos_busca:   # termos vêm do perfil.json
               dados = self._get("https://api.exemplo.com/vagas", params={"q": termo}).json()
               self._pausa()
               vagas.extend(self._converter(item) for item in dados["resultados"])
           return [v for v in vagas if v]           # _criar_vaga devolve None se faltar título/URL

       def _converter(self, item: dict) -> Vaga | None:
           return self._criar_vaga(
               titulo=item["titulo"],
               empresa=item.get("empresa", ""),
               local=item.get("cidade", ""),
               modalidade=detectar_modalidade(item["titulo"], item.get("descricao")),
               url=item["link"],
               data_publicacao=para_iso_utc(item.get("publicado_em")),
               descricao=limpar_html(item.get("descricao")),
           )
   ```

2. Registre a fonte em `collector/sources/__init__.py`, na lista `TODAS_AS_FONTES`.
3. Ative em `collector/config.py` → `FONTES_ATIVAS["minha_fonte"] = True`.
4. Se a fonte precisar de key, leia com `os.environ.get(...)` e adicione:
   - no `.env.example`;
   - no bloco `env:` do passo "Coletar vagas" em `.github/workflows/coletar.yml`;
   - nos Secrets do repositório.

Não é preciso calcular score, "combina/falta" nem deduplicar dentro da fonte: o `main.py` faz isso para todas.

---

## Como funciona

### Score (0–100)

| Regra | Pontos |
|---|---|
| Cada skill principal do perfil citada no título/descrição | +15 (máx. 45) |
| Cada skill secundária do perfil | +10 (máx. 20) |
| Vaga numa das `cidades_presencial` | +20 |
| Remota (se `aceita_remoto`), ou híbrida numa das `cidades_hibrido` | +10 |
| Título com um nível aceito **ou** sem menção de nível | +15 |
| Vaga pede mais que `anos_experiencia` + 1 ano (ex.: perfil com 3 anos, vaga pede 5–6) | −15 (−30 se pedir 7+) |
| Título com nível fora de `niveis_aceitos` (sênior, sr., especialista, tech lead, arquiteto, estágio...) | −100 (descarta) |

Só entram vagas com **score ≥ 30**. Os pesos ficam em `collector/config.py`, e as regex em `collector/scoring.py`. As comparações ignoram maiúsculas, acentos e pontuação. A cidade é comparada pelo primeiro pedaço do local, para "Campinas, Estado de São Paulo" não contar como São Paulo.

### Combina / Falta

O dicionário em `collector/skills.py` reconhece cerca de 55 tecnologias com sinônimos ("React.JS", "ReactJS" e "react" são a mesma coisa; "JavaScript" não conta como "Java") e implicações ("Next.js" conta como React; quem sabe TypeScript sabe JavaScript).

- **Combina:** skills citadas na vaga que estão no currículo.
- **Falta:** skills citadas na vaga que não aparecem no currículo.
- **% compatível** (no painel) = combina ÷ (combina + falta).
- **Pede N anos:** quando a descrição diz algo como "3+ anos de experiência" ou "mínimo de 5 anos". Valores acima de 10 são ignorados ("empresa com 30 anos de mercado").

A cada execução, todas as vagas do JSON são reanalisadas com o perfil atual. Então, ao editar o `perfil.json`, os scores antigos também são recalculados.

### Deduplicação e histórico

- `id` = SHA1 de título + empresa normalizados. Assim, a mesma vaga vinda de duas fontes vira uma só, e fica a de maior score. Quando a empresa não é informada, o local entra no hash para não fundir vagas diferentes.
- Vagas já conhecidas mantêm a `data_coleta` original.
- Vaga não vista há **mais de 14 dias** recebe `"expirada": true`, mas continua no arquivo.
- Vaga não vista há **mais de 60 dias** é removida, para o JSON não crescer para sempre. Ajuste ou desligue (0) em `DIAS_PARA_REMOVER`.
- O arquivo só é regravado se a lista de vagas mudou: rodar duas vezes seguidas não duplica nada nem gera commit vazio.
- Se **todas** as fontes falharem, o coletor sai com erro e não mexe no arquivo.

### Observações sobre as fontes

- **Gupy:** o endpoint `portal.api.gupy.io/api/job` responde 404. O coletor usa `employability-portal.gupy.io/api/v1/jobs`, o mesmo que o portal usa hoje. Não é uma API documentada; se quebrar, veja no DevTools (aba Network) qual URL o portal chama.
- **InfoJobs:** o HTML da busca vem renderizado do servidor, então a fonte está ativa. A busca mostra só um resumo de ~150 caracteres por vaga, curto demais para achar skills: por isso o coletor abre a **página de cada vaga** para ler a descrição completa, com a lista de habilidades e a experiência pedida. Vagas já descartadas pelo título (sênior, estágio...) não são abertas. Limite: `INFOJOBS_MAX_DETALHES = 60` páginas por execução (~1,5 min). Se passar a exigir JavaScript, desative-a em `FONTES_ATIVAS` e siga as instruções no topo de `collector/sources/infojobs.py` para migrar para Playwright.
- A descrição da Adzuna vem resumida, então o "combina/falta" dela é menos completo que o da Gupy e do InfoJobs, que trazem a descrição inteira.
- Quando a mesma vaga (mesmo título e empresa) aparece mais de uma vez com o mesmo score, fica a de menor URL. O desempate é fixo para o JSON não mudar à toa entre execuções.
- O `docs/data/vagas.json` é gerado pelo coletor. Se o arquivo não existir, a próxima coleta cria um novo do zero.
