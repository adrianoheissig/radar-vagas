# 📡 Radar de Vagas TI

Busca automática de vagas de **Desenvolvedor(a) Fullstack/Frontend júnior-pleno** em várias fontes. As vagas recebem um score conforme o perfil e aparecem num painel web estático hospedado no GitHub Pages.

- **Perfil-alvo:** React, Angular, TypeScript, Node.js, Java, MySQL, Firebase, Figma · ~3 anos de experiência
- **Local:** presencial em Guarulhos, híbrido em São Paulo (capital) ou 100% remoto
- **Fontes:** Adzuna (API oficial), JSearch/RapidAPI (opcional), Gupy (API pública do portal), InfoJobs (scraping)

> O painel **só lista** as vagas e leva ao link oficial. Não existe candidatura nem login automatizado em nenhum portal.

```
radar-vagas/
├── collector/                 # Coletor em Python 3.12
│   ├── main.py                # ponto de entrada: python -m collector.main
│   ├── config.py              # termos de busca, pesos do score, fontes ativas
│   ├── models.py              # dataclass Vaga
│   ├── scoring.py             # regras de score
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

O plano gratuito dá cerca de **200 requisições por mês**. O coletor faz 2 por execução (~180/mês). Se aumentar `JSEARCH_CONSULTAS` em `collector/config.py`, a cota acaba antes do fim do mês. Sem a key, a fonte é simplesmente pulada (aparece um aviso no log).

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
- **Filtros:** texto livre, modalidade, fonte, score mínimo, ocultar expiradas e ordenação. Os filtros ficam salvos no navegador.
- **Menu ⋯ → Exportar/Importar status:** gera um JSON para levar seus status do computador para o celular (ou vice-versa).

---

## 4. Rodar localmente

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

## 5. Adicionar uma nova fonte de vagas

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
           dados = self._get("https://api.exemplo.com/vagas", params={"q": "react"}).json()
           self._pausa()
           for item in dados["resultados"]:
               vaga = self._criar_vaga(          # retorna None se faltar título/URL
                   titulo=item["titulo"],
                   empresa=item.get("empresa", ""),
                   local=item.get("cidade", ""),
                   modalidade=detectar_modalidade(item["titulo"], item.get("descricao")),
                   url=item["link"],
                   data_publicacao=para_iso_utc(item.get("publicado_em")),
                   descricao=limpar_html(item.get("descricao")),
               )
               if vaga:
                   vagas.append(vaga)
           return vagas
   ```

2. Registre a fonte em `collector/sources/__init__.py`, na lista `TODAS_AS_FONTES`.
3. Ative em `collector/config.py` → `FONTES_ATIVAS["minha_fonte"] = True`.
4. Se a fonte precisar de key, leia com `os.environ.get(...)` e adicione:
   - no `.env.example`;
   - no bloco `env:` do passo "Coletar vagas" em `.github/workflows/coletar.yml`;
   - nos Secrets do repositório.

Não é preciso calcular score nem deduplicar dentro da fonte: o `main.py` faz isso para todas.

---

## Como funciona

### Score (0–100)

| Regra | Pontos |
|---|---|
| Cada skill principal no título/descrição: react, angular, typescript, node | +15 (máx. 45) |
| Cada skill secundária: java, mysql, firebase, figma | +10 (máx. 20) |
| Local contém "Guarulhos" | +20 |
| Remoto, ou híbrido com local em "São Paulo" | +10 |
| Título com júnior/jr/pleno **ou** sem menção de senioridade | +15 |
| Título com sênior, senior, sr., especialista, tech lead, arquiteto(a), estágio, estagiário(a) | −100 (descarta) |

Só entram vagas com **score ≥ 30**. Os pesos ficam em `collector/config.py`, e as regex em `collector/scoring.py`. As comparações ignoram maiúsculas, acentos e pontuação.

### Deduplicação e histórico

- `id` = SHA1 de título + empresa normalizados. Assim, a mesma vaga vinda de duas fontes vira uma só, e fica a de maior score. Quando a empresa não é informada, o local entra no hash para não fundir vagas diferentes.
- Vagas já conhecidas mantêm a `data_coleta` original.
- Vaga não vista há **mais de 14 dias** recebe `"expirada": true`, mas continua no arquivo.
- Vaga não vista há **mais de 60 dias** é removida, para o JSON não crescer para sempre. Ajuste ou desligue (0) em `DIAS_PARA_REMOVER`.
- O arquivo só é regravado se a lista de vagas mudou: rodar duas vezes seguidas não duplica nada nem gera commit vazio.
- Se **todas** as fontes falharem, o coletor sai com erro e não mexe no arquivo.

### Observações sobre as fontes

- **Gupy:** o endpoint `portal.api.gupy.io/api/job` responde 404. O coletor usa `employability-portal.gupy.io/api/v1/jobs`, o mesmo que o portal usa hoje. Não é uma API documentada; se quebrar, veja no DevTools (aba Network) qual URL o portal chama.
- **InfoJobs:** o HTML da busca vem renderizado do servidor, então a fonte está ativa. Se passar a exigir JavaScript, desative-a em `FONTES_ATIVAS` e siga as instruções no topo de `collector/sources/infojobs.py` para migrar para Playwright.
- O `docs/data/vagas.json` inicial tem **5 vagas fictícias** (links para `example.com`) só para o painel funcionar antes da primeira coleta. A primeira execução real mistura essas vagas com as reais, e as fictícias expiram sozinhas. Se preferir, apague o arquivo antes de rodar a primeira coleta.
