# Fluxo Barber — Plano do Projeto

**Objetivo:** substituir a planilha Excel `fluxo_caixa.xlsx` por um app desktop local (`.exe`) para gestão financeira da barbearia **brodz**. Offline, simples de usar, dados íntegros e dashboards visuais de fechamento de dia, mês e ano, com **controle completo de assinaturas** e comportamento de consumo dos clientes assinantes.

**Stack (MVP):** Python 3.11+ • CustomTkinter (UI) • SQLite (dados) • matplotlib (gráficos) • PyInstaller (empacotamento).

> A stack é intencionalmente leve para o MVP de validação. Quando o negócio validar e for expandido para um modelo replicável, avaliaremos migrar a UI (PySide6 / Tauri) e o DB (PostgreSQL/Supabase) sem remodelar o domínio.

---

## 1. Decisões tomadas

| Decisão | Escolha | Impacto |
|---|---|---|
| Detalhe do recebimento | **Por atendimento/serviço** | Cada corte/barba/combo é uma linha. Permite ticket médio, serviço mais vendido, hora de pico. |
| Despesas | **Categorias + itens frequentes + genérica** | Itens recorrentes (água, lâmina, copo, bala…) ficam pré-cadastrados como botões de 1 clique; fallback genérico sempre disponível. |
| Contas bancárias | **Apenas forma de pagamento** | PIX / Dinheiro / Maquininha — sem saldo por banco. Aposenta a aba "Cadastro" de múltiplos bancos. |
| Usuários | **Só o dono (sem login)** | Sem atrito. Multi-usuário fica para a fase pós-validação. |
| **Clientes** | **Opcional em atendimentos avulsos, obrigatório em assinantes** | Cadastro leve (nome + telefone). Só vira obrigatório quando o atendimento está vinculado a um plano. |
| **Assinaturas** | **Módulo de 1ª classe** | 5 planos mensais hoje + abertos para novos. Controle de uso, inadimplência e upsell. |

### 1.1 Modelo de Assinatura (o coração estratégico)

O negócio da brodz já pratica **planos mensais fixos**. O valor estratégico de tratarmos assinatura como módulo de primeira classe é:

1. **Contabilizar recorrência separadamente** do faturamento avulso — a famosa "MRR" (Monthly Recurring Revenue). Saber quanto entra garantido todo mês é pilar de previsão.
2. **Medir quantas vezes cada assinante usou o plano no mês** — quem corta muito "custa caro" ao negócio; quem corta pouco é margem positiva.
3. **Identificar oportunidades de upsell** — assinante que veio 4× no mês (consumindo 100% do plano) é candidato perfeito pra comprar produtos (pomada, minoxidil, hidratação extra). Assinante que veio 1× é alvo de campanha pra "aproveitar o plano".
4. **Calcular LTV real por cliente** — quanto cada assinante gasta em extras (produtos + serviços fora do plano) além da mensalidade. O relatório responde: "quem são meus 10 clientes mais lucrativos?".

### 1.2 Planos de assinatura atuais (brodz)

| Plano | Preço mensal | Serviços inclusos | Quantidade |
|---|---|---|---|
| 2 Cortes | R$ 60 | Corte de cabelo | 2× |
| 4 Cortes | R$ 112 | Corte de cabelo | 4× |
| Corte + Barba | R$ 100 | Corte + Barba | ilimitado |
| 4× Corte + Barba | R$ 192 | Corte + Barba | 4× |
| 4× Corte + Sobrancelha | R$ 140 | Corte de cabelo + Sobrancelhas | 4× |

> **Nota sobre preços:** o catálogo acima é o atual e está *intencionalmente flexível*. Já foi sinalizado que "4 Cortes" pode migrar de R$ 112 para R$ 105 no futuro por não estar em faixa adequada. O app trata preços como dado editável em runtime — nenhuma mudança de código é necessária para reajustar.
> **Nota sobre cotas:** "Corte + Barba R$ 100" entra como **ilimitado** (campo `qtd_servicos_mes = NULL` no schema) conforme informado. Se o dono perceber abuso, basta editar a quantidade em Configurações — a lógica de cota já está pronta.

### 1.3 Pontos de dor da planilha atual que o app resolve

- Receita aparece como "fechamento diário" — perde-se análise de ticket, serviço mais rentável, quem é assinante.
- **Zero visibilidade de assinaturas**: na planilha não dá pra saber quem está ativo, quem pagou a mensalidade, quem sumiu. Tudo paralelo em caderno ou na memória.
- Despesas em texto livre (`lamina`, `copo`, `agua galao`) — não dá pra responder "quanto gastei de insumo em Março".
- Datas inconsistentes (algumas linhas usam `2025`, outras `2026`, uma `1900`) — falta validação.
- Dashboard mensal exige copiar valores entre abas — suscetível a erro humano.
- Arquivo único compartilhado é frágil (sobrescrita, versões divergentes, sem histórico).

---

## 2. Arquitetura

Aplicação em camadas, cada uma com responsabilidade única. Facilita testes e troca futura de UI/DB.

```
fluxo_barber/
├── app/
│   ├── main.py                 # entry point (cria janela principal)
│   ├── ui/                     # CustomTkinter: apenas apresentação
│   │   ├── app_window.py       # shell (sidebar + área central)
│   │   ├── screens/
│   │   │   ├── dashboard.py
│   │   │   ├── lancamento_rapido.py
│   │   │   ├── receitas.py
│   │   │   ├── despesas.py
│   │   │   ├── clientes.py
│   │   │   ├── assinaturas.py
│   │   │   ├── relatorios.py
│   │   │   └── configuracoes.py
│   │   └── widgets/            # botões de serviço, KPI cards, cliente_picker, etc.
│   ├── services/               # regras de negócio (sem Tk, sem SQL)
│   │   ├── receita_service.py
│   │   ├── despesa_service.py
│   │   ├── cliente_service.py
│   │   ├── assinatura_service.py       # inclui lógica de cobrança, uso, upsell
│   │   ├── fechamento_service.py
│   │   └── relatorio_service.py
│   ├── repositories/           # SQL isolado aqui
│   │   ├── db.py               # conexão SQLite, migrações
│   │   ├── receita_repo.py
│   │   ├── despesa_repo.py
│   │   ├── cliente_repo.py
│   │   ├── assinatura_repo.py
│   │   └── catalogo_repo.py
│   ├── domain/                 # dataclasses puras
│   │   ├── receita.py
│   │   ├── despesa.py
│   │   ├── cliente.py
│   │   ├── assinatura.py
│   │   └── enums.py            # FormaPagamento, CategoriaDespesa, StatusAssinatura
│   └── utils/
│       ├── formato.py          # R$, datas pt-BR
│       ├── validators.py
│       └── backup.py
├── data/
│   ├── fluxo_barber.db         # SQLite (criado no 1º run)
│   └── backups/                # backups automáticos
├── resources/                  # ícones, logo
├── tests/                      # pytest
├── build/                      # artefatos do PyInstaller
├── requirements.txt
├── pyinstaller.spec
└── README.md
```

**Princípios:**

- UI nunca fala com o DB direto — sempre via `services`.
- `services` nunca usa `tkinter` — só Python puro, testável.
- `repositories` é o único lugar com SQL.
- `domain` são dataclasses imutáveis; funcionam como DTO entre camadas.

---

## 3. Modelo de dados (SQLite)

Valores em **centavos (INTEGER)** para evitar erros de arredondamento. Datas em ISO-8601 (`YYYY-MM-DD`). Foreign keys ligadas.

```sql
-- 3.1 CATÁLOGO DE SERVIÇOS (avulsos e inclusos em planos)
CREATE TABLE servico (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nome          TEXT    NOT NULL UNIQUE,
    preco_padrao  INTEGER NOT NULL,             -- centavos
    ativo         INTEGER NOT NULL DEFAULT 1,
    ordem         INTEGER NOT NULL DEFAULT 0,   -- ordenação na tela de lançamento
    categoria_servico TEXT,                      -- "Corte", "Barba", "Coloração", "Penteado", "Tratamento", "Combo", "Prótese"
    criado_em     TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- 3.2 PLANOS DE ASSINATURA
CREATE TABLE plano_assinatura (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    nome             TEXT    NOT NULL UNIQUE,     -- "4 Cortes", "Corte + Barba", etc.
    descricao        TEXT,                        -- detalhe legível
    preco_mensal     INTEGER NOT NULL,            -- centavos
    qtd_servicos_mes INTEGER,                     -- NULL = ilimitado
    ativo            INTEGER NOT NULL DEFAULT 1,
    criado_em        TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Quais serviços cada plano cobre (N:N)
CREATE TABLE plano_servico (
    plano_id   INTEGER NOT NULL REFERENCES plano_assinatura(id) ON DELETE CASCADE,
    servico_id INTEGER NOT NULL REFERENCES servico(id),
    PRIMARY KEY (plano_id, servico_id)
);

-- 3.3 CLIENTES
CREATE TABLE cliente (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    nome       TEXT    NOT NULL,
    telefone   TEXT,                            -- opcional, mas útil p/ campanha de retenção
    aniversario TEXT,                           -- YYYY-MM-DD opcional
    observacao TEXT,
    criado_em  TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_cliente_nome ON cliente(nome);

-- 3.4 ASSINATURAS (cliente × plano, período)
CREATE TABLE assinatura (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id     INTEGER NOT NULL REFERENCES cliente(id),
    plano_id       INTEGER NOT NULL REFERENCES plano_assinatura(id),
    data_inicio    TEXT    NOT NULL,            -- YYYY-MM-DD
    data_fim       TEXT,                        -- NULL = ativa
    dia_cobranca   INTEGER NOT NULL DEFAULT 1,  -- 1..28
    criado_em      TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_assinatura_cliente ON assinatura(cliente_id);
CREATE INDEX idx_assinatura_ativa   ON assinatura(data_fim);

-- 3.5 PAGAMENTOS DE MENSALIDADE (1 por mês de vigência)
CREATE TABLE pagamento_assinatura (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    assinatura_id   INTEGER NOT NULL REFERENCES assinatura(id),
    mes_referencia  TEXT    NOT NULL,            -- YYYY-MM
    data_pagamento  TEXT    NOT NULL,
    valor           INTEGER NOT NULL,
    forma_pagamento TEXT    NOT NULL CHECK (forma_pagamento IN ('PIX','DINHEIRO','MAQUININHA')),
    criado_em       TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (assinatura_id, mes_referencia)       -- impede pagamento duplicado do mesmo mês
);
CREATE INDEX idx_pgto_assinatura_mes ON pagamento_assinatura(mes_referencia);

-- 3.6 RECEITA POR ATENDIMENTO (avulso OU consumo de plano)
CREATE TABLE receita (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    data             TEXT    NOT NULL,           -- YYYY-MM-DD
    servico_id       INTEGER NOT NULL REFERENCES servico(id),
    cliente_id       INTEGER          REFERENCES cliente(id),   -- NULL = cliente anônimo
    assinatura_id    INTEGER          REFERENCES assinatura(id),-- NOT NULL se coberto por plano
    valor            INTEGER NOT NULL,           -- 0 quando coberto 100% pelo plano; >0 se avulso/extra
    forma_pagamento  TEXT    CHECK (forma_pagamento IN ('PIX','DINHEIRO','MAQUININHA')),
                                                 -- pode ser NULL quando valor=0 (não houve caixa)
    observacao       TEXT,
    criado_em        TEXT    NOT NULL DEFAULT (datetime('now')),
    editado_em       TEXT
);
CREATE INDEX idx_receita_data        ON receita(data);
CREATE INDEX idx_receita_cliente     ON receita(cliente_id);
CREATE INDEX idx_receita_assinatura  ON receita(assinatura_id);

-- 3.7 CATEGORIAS DE DESPESA (fixas)
CREATE TABLE categoria_despesa (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    nome  TEXT    NOT NULL UNIQUE,
    icone TEXT,
    ativo INTEGER NOT NULL DEFAULT 1
);

-- 3.8 ITENS FREQUENTES DE DESPESA (1-clique no modal)
CREATE TABLE item_despesa_frequente (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    descricao      TEXT    NOT NULL UNIQUE,      -- "Água galão", "Lâmina", "Copo", "Bala"
    categoria_id   INTEGER NOT NULL REFERENCES categoria_despesa(id),
    valor_sugerido INTEGER,                       -- centavos; opcional
    vezes_usado    INTEGER NOT NULL DEFAULT 0,   -- contador p/ ordenar por frequência
    ativo          INTEGER NOT NULL DEFAULT 1
);

-- 3.9 DESPESAS
CREATE TABLE despesa (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    data             TEXT    NOT NULL,
    categoria_id     INTEGER NOT NULL REFERENCES categoria_despesa(id),
    item_frequente_id INTEGER          REFERENCES item_despesa_frequente(id),  -- NULL se genérica
    descricao        TEXT    NOT NULL,           -- copiada do item ou texto livre
    valor            INTEGER NOT NULL,
    forma_pagamento  TEXT    NOT NULL CHECK (forma_pagamento IN ('PIX','DINHEIRO','MAQUININHA')),
    criado_em        TEXT    NOT NULL DEFAULT (datetime('now')),
    editado_em       TEXT
);
CREATE INDEX idx_despesa_data      ON despesa(data);
CREATE INDEX idx_despesa_categoria ON despesa(categoria_id);

-- 3.10 AUDITORIA
CREATE TABLE auditoria (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    tabela       TEXT    NOT NULL,
    registro_id  INTEGER NOT NULL,
    acao         TEXT    NOT NULL,                -- 'INSERT' | 'UPDATE' | 'DELETE'
    payload      TEXT    NOT NULL,                -- JSON
    timestamp    TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- 3.11 CONFIG CHAVE-VALOR
CREATE TABLE config (
    chave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);
```

### 3.12 Seed inicial (aplicado no 1º run)

**Serviços (catálogo completo informado):**

```
Alisante                        R$  20,00   Tratamento
Barba                           R$  25,00   Barba
Barboterapia                    R$  35,00   Barba
Bigode                          R$  10,00   Barba
Cacheado dedo liss              R$  30,00   Tratamento
Camuflagem                      R$  20,00   Coloração
Cavanhaque                      R$  15,00   Barba
Corte + Barba                   R$  60,00   Combo
Corte + Bigode                  R$  45,00   Combo
Corte + Cavanhaque              R$  50,00   Combo
Corte + Barba + Sobrancelha     R$  70,00   Combo
Corte + Sobrancelha             R$  45,00   Combo
Corte + Alisamento              R$  55,00   Combo
Corte de cabelo                 R$  35,00   Corte
Corte e penteado selado         R$  60,00   Combo
Depilação nariz                 R$  10,00   Estética
Frisado                         R$  50,00   Tratamento
Hidratação térmica              R$  25,00   Tratamento
Limpeza de pele                 R$  20,00   Estética
Luzes                           R$  60,00   Coloração
Luzes platinada                 R$  70,00   Coloração
Manutenção prótese              R$ 150,00   Prótese
Matização                       R$  10,00   Coloração
Penteado afro nudred            R$  10,00   Penteado
Penteado dimil                  R$  25,00   Penteado
Penteado fio a fio              R$  60,00   Penteado
Penteado franjinha              R$  25,00   Penteado
Penteado selado                 R$  25,00   Penteado
Pezinho                         R$  15,00   Corte
Pigmentação                     R$  15,00   Coloração
Platinado                       R$ 130,00   Coloração
Progressiva                     R$  60,00   Tratamento
Prótese fio a fio afro          R$ 400,00   Prótese
Prótese média franja            R$  80,00   Prótese
Reflexo                         R$  60,00   Coloração
Relaxamento cachos              R$  20,00   Tratamento
Sobrancelhas                    R$  10,00   Estética
```

> Tudo editável em Configurações. Sugiro ordenar os botões de lançamento pelos **mais usados** (Corte, Corte+Barba, Barba, Sobrancelhas, Pezinho) no topo, e esconder os raros atrás de um botão "Mais serviços…".

**Planos de assinatura:**

| Nome | Preço/mês | Qtd | Serviços inclusos |
|---|---|---|---|
| 2 Cortes | R$ 60 | 2 | Corte de cabelo |
| 4 Cortes | R$ 112 | 4 | Corte de cabelo |
| Corte + Barba | R$ 100 | ilimitado | Corte + Barba |
| 4× Corte + Barba | R$ 192 | 4 | Corte + Barba |
| 4× Corte + Sobrancelha | R$ 140 | 4 | Corte de cabelo, Sobrancelhas |

**Categorias de despesa:**

| Nome | Ícone | Exemplos típicos da planilha |
|---|---|---|
| Insumos / Produtos | 🧴 | lâmina, álcool, pano, embalagem, tinta, desinfetante, cloro, filtro de café |
| Bebidas & Alimentos | 🥤 | bala, café, pirulito, Bally, Sprite, Coca, guaraná, tubaína, água, açúcar |
| Infraestrutura | 🏠 | água (galão), gás, aluguel, energia, internet |
| Manutenção | 🔧 | ferro das grades, cano, faquinha |
| Impostos | 📄 | DAS, ISS |
| Pessoal | 👤 | pró-labore, vale, adiantamento (ex: "henrique vale", "mando no pix") |
| Outros | 📦 | pilhaa, gastos genéricos, despesas de terceiros |

**Itens frequentes (botões de 1 clique no modal de despesa):**

`Água galão (R$ 13)`, `Lâmina (R$ 30)`, `Copo (R$ 6)`, `Açúcar (R$ 18)`, `Café (R$ 55)`, `Bala (R$ 4)`, `Pirulito (R$ 8)`, `Álcool (R$ 10)`, `Pano (R$ 15)`, `Embalagem (R$ 30)`, `Desinfetante`, `Cloro`, `Filtro de café`.

> Todos com preço "sugerido" — o dono pode sobrescrever. A lista ordena pelos **mais usados**, então as pilhas de lâmina e cafés dominam o topo naturalmente.

**Config:**

- `nome_empresa = brodz`
- `meta_mensal = 0` (dono configura depois)
- `ano_contabil = ano corrente`

---

## 4. Telas e fluxos (UX)

Prioridade #1: **velocidade no lançamento**. Alvo: registrar um atendimento em **< 5 segundos**, assinatura em **< 3 segundos** (cliente selecionado + botão do plano).

### 4.1 Layout geral

Janela única com sidebar fixa à esquerda e conteúdo à direita. Tema escuro CustomTkinter por padrão, alternável.

```
┌──────────────────────────────────────────────────────────────┐
│ [🏠 Dashboard]       │                                        │
│ [⚡ Lançar]          │                                        │
│ [📈 Receitas]        │                                        │
│ [💸 Despesas]        │        CONTEÚDO DA TELA ATIVA         │
│ [👥 Clientes]        │                                        │
│ [📋 Assinaturas]     │                                        │
│ [📊 Relatórios]      │                                        │
│ [⚙ Configurações]    │                                        │
│                      │                                        │
│ brodz • 17/04/26    │                                        │
└──────────────────────────────────────────────────────────────┘
```

### 4.2 Tela "⚡ Lançar" (tela padrão ao abrir)

Três abas no topo: **Atendimento** • **Assinante** • **Despesa**.

**Aba Atendimento (cliente avulso ou anônimo):**

- Campo opcional no topo: `Cliente: [Selecionar… ⬇]` — autocomplete por nome. Em branco = anônimo.
- Grid com botões grandes (80×80 px) dos serviços **ativos** ordenados por uso. Cada botão: nome + preço.
- Clique → modal mínimo: valor editável, forma de pagamento (3 toggles PIX/Dinheiro/Maquininha), `observação` opcional. Enter salva.
- Barra no topo: "Hoje: **R$ 820** em 14 atendimentos (3 assinantes, 11 avulsos)".

**Aba Assinante (fluxo otimizado):**

- Passo 1: seleciona cliente (autocomplete). Só lista clientes **com assinatura ativa**.
- Passo 2: app detecta o plano ativo e mostra card:
  ```
  Cliente: João Silva
  Plano: 4× Corte + Barba (R$ 192/mês)
  Usado neste mês: 2 de 4
  [ Registrar CORTE + BARBA ]  ← 1 clique, valor = 0, atendimento_id → plano
  [ + Adicionar EXTRA ]         ← cobra à parte
  ```
- Se o assinante já estourou a cota (ex: 5/4): o botão muda para "Registrar como EXTRA R$ 60" e um aviso amigável aparece para o dono.

**Aba Despesa:**

- Grid de itens frequentes (botões de 1 clique com valor sugerido). Ex: `💧 Água galão R$13`, `🪒 Lâmina R$30`, `☕ Café R$55`.
- Botão `+ Despesa genérica` → modal com categoria (select), descrição livre com autocomplete, valor, forma de pagamento.
- Lista das despesas do dia logo abaixo, com editar/excluir.

**Atalhos de teclado:**

- `A` → aba Atendimento, `S` → Assinante, `D` → Despesa.
- `1..9` → serviço/item correspondente da aba ativa.
- `Esc` fecha modal.

### 4.3 Tela "📈 Receitas"

Grid editável com filtro de período (hoje / semana / mês / customizado), busca por cliente, flag **"Somente avulsos" / "Somente assinantes"**. Colunas: Data, Cliente, Serviço, Valor, Forma, Plano (se houver). Export CSV.

### 4.4 Tela "💸 Despesas"

Grid similar, com filtro por categoria. Coluna `Item Frequente` para fácil leitura.

### 4.5 Tela "👥 Clientes"

- Lista pesquisável (nome, telefone).
- CRUD de cliente.
- Ao abrir um cliente: mini-dashboard pessoal
  - Total investido (últimos 12 meses).
  - Breakdown: mensalidade / avulsos / extras.
  - Nº de visitas no mês atual vs. cota do plano (se assinante).
  - Timeline dos últimos atendimentos.
  - Botão `Nova assinatura`.

### 4.6 Tela "📋 Assinaturas"

- Lista de assinaturas **ativas** no topo, **inativas/canceladas** abaixo.
- Cada linha: cliente, plano, desde, status de pagamento do mês (✅ pago / ⚠️ pendente / ❌ atrasado), uso no mês (ex: `2/4`).
- Ações: `Registrar pagamento`, `Cancelar assinatura`, `Mudar de plano`.
- Botão `+ Nova assinatura` → wizard: cliente → plano → data de início → dia de cobrança → confirma.
- Aba **"Pendências do mês"**: lista de quem ainda não pagou a mensalidade do mês vigente, com botão rápido "Registrar pagamento".

### 4.7 Tela "📊 Relatórios"

Seletor de período com presets: **Dia**, **Mês atual**, **Mês anterior**, **Ano**, **Customizado**. Gera:

- DRE resumida (Receita Avulsa + MRR – Despesa = Resultado).
- Receita por serviço (tabela + pizza).
- Receita por origem: **MRR vs. Avulsos vs. Extras de assinantes**.
- Despesa por categoria (tabela + barras).
- Série diária de receita/despesa (linha).
- Ranking de clientes por LTV.
- Assinantes por status de pagamento.
- **Exportar PDF** e **Exportar Excel** (reconstitui o formato da planilha atual para continuidade).

### 4.8 Tela "⚙ Configurações"

- **Serviços** (CRUD: nome, preço, categoria, ativo, ordem).
- **Planos de assinatura** (CRUD: nome, preço, qtd, serviços inclusos).
- **Categorias de despesa** e **Itens frequentes** (CRUD).
- Nome da empresa, meta mensal, tema, formato de data.
- Backup manual e restaurar backup. Diretório de backups.

---

## 5. Dashboard (Prioridade #3)

Tela principal ao abrir, com 4 abas: **Hoje • Mês • Ano • Assinantes**.

### 5.1 Aba "Hoje"

- 4 KPI cards: **Receita do dia**, **Despesa do dia**, **Resultado do dia**, **Atendimentos** (com split avulso/assinante).
- Split por forma de pagamento (PIX / Dinheiro / Maquininha) — bate com o caixa físico no fim do expediente.
- Timeline dos atendimentos do dia.
- Lista de despesas do dia.
- Botão "Fechar dia" — confirma os números, registra timestamp.

### 5.2 Aba "Mês"

- KPI cards: **Faturamento total**, **MRR (mensalidades)**, **Avulsos**, **Extras de assinantes**, **Despesas**, **Sobra financeira**, **Ticket médio**, **Dias trabalhados**.
- Gráfico de barras diário (receita × despesa).
- Top 5 serviços do mês.
- Top 5 categorias de despesa.
- Barra de progresso da meta mensal.
- Comparativo com mês anterior (Δ %).

### 5.3 Aba "Ano"

- 12 cards mensais (Jan..Dez) à la aba Análises da planilha: Faturamento / Pagamentos / Sobra.
- Gráfico de linha anual (receita × despesa × MRR).
- Totais anuais + melhor mês / pior mês.

### 5.4 Aba "Assinantes" 🔑

É aqui que o app **passa da planilha para ferramenta de negócio**.

- **KPIs:** Nº de assinantes ativos, MRR atual, Ticket médio de extras por assinante, Taxa de inadimplência do mês.
- **Cota de uso vs. plano** — gráfico de barras empilhadas mostrando, para cada plano, quantos % da cota foi usado pelos clientes em média.
- **Tabela "Uso do mês":** cada assinante com usado/cota e um indicador de cor:
  - 🟢 **Ocioso** (usou < 50% do plano) → candidato a campanha de retenção.
  - 🟡 **No limite** (50–100%) → ok.
  - 🔴 **Consumiu 100%+** → **oportunidade de upsell**: o plano virou "commodity" para ele, é hora de oferecer produtos, serviços premium, upgrade de plano.
- **Alertas automáticos:**
  - "3 assinantes não pagaram a mensalidade de abril."
  - "João consumiu 4/4 cortes e voltou 3× como extra — candidato ao plano ilimitado."
  - "Maria não aparece há 6 semanas — risco de cancelamento."
- **Ranking de LTV** dos 10 clientes mais rentáveis.

---

## 6. Governança (Prioridade #2 — dados íntegros)

1. **Validações de entrada**
   - Data não pode ser futura (>hoje) sem confirmação explícita.
   - Valor > 0 em avulsos; em assinatura coberta, valor = 0 e forma_pagamento = NULL.
   - Forma de pagamento obrigatória em avulsos/extras.
   - Cliente obrigatório se `assinatura_id` presente.
   - `UNIQUE(assinatura_id, mes_referencia)` em `pagamento_assinatura` evita duplicar cobrança.
   - Serviço registrado como cobertura de plano deve estar em `plano_servico` do plano ativo.
2. **Soft delete + auditoria** — toda exclusão/edição grava o estado anterior em `auditoria` (JSON). Recuperável.
3. **Backup automático**
   - Ao abrir o app: se o último backup tem >24h, cria `data/backups/fluxo_barber_YYYYMMDD_HHMMSS.db`.
   - Mantém últimos 30 backups (rotação).
   - Backup manual sob demanda.
4. **Integridade do DB** — `PRAGMA foreign_keys = ON`, `PRAGMA journal_mode = WAL`.
5. **Single instance lock** — impede abrir duas janelas que escreveriam no mesmo DB.
6. **Exportação Excel** — reconstrói a planilha mensal + Análises (com abas extras de Clientes e Assinaturas).

---

## 7. Empacotamento (.exe)

- **PyInstaller** com `--onefile --windowed --icon resources/logo.ico`.
- `pyinstaller.spec` customizado incluindo `resources/` e o schema SQL inicial.
- DB fica em `%APPDATA%/FluxoBarber/fluxo_barber.db` — permite atualizar o app sem perder dados.
- Primeiro run: cria a pasta em AppData, roda schema + seed.
- Tamanho esperado: ~40–60 MB.
- Instalador futuro via Inno Setup.

---

## 8. Roadmap em fases

### Fase 0 — Fundação (1–2 dias)
- Estrutura de pastas + `requirements.txt`.
- SQLite + schema + seed (serviços, planos, categorias, itens frequentes).
- Repositórios + services com testes unitários mínimos.

### Fase 1 — MVP Lançamento (3–4 dias)
- Shell da UI (sidebar + navegação).
- Tela **Lançar** — abas Atendimento e Despesa (sem assinante ainda).
- Telas **Receitas** e **Despesas** com grid, filtro, edição, exclusão.
- Tela **Configurações** (serviços, categorias, itens frequentes, nome da empresa).
- Backup automático + manual.

### Fase 2 — Módulo de Assinaturas (3 dias)
- Tabelas `cliente`, `plano_assinatura`, `assinatura`, `pagamento_assinatura`.
- Telas **Clientes** e **Assinaturas**.
- Aba **Assinante** na tela Lançar.
- KPIs de uso de plano e alertas.

### Fase 3 — Dashboard & Relatórios (2–3 dias)
- Dashboard 4 abas (Hoje/Mês/Ano/Assinantes).
- Relatórios com gráficos matplotlib.
- Exportação PDF e Excel.

### Fase 4 — Empacotamento e piloto (1 dia)
- PyInstaller + ícone + AppData.
- Instalar na máquina da barbearia, rodar `scripts/migrar_planilha.py`.
- Acompanhar 2 semanas de uso real, coletar feedback.

### Fase 5 (pós-validação) — Evoluções
- Comissão por atendimento + multi-usuário (login/PIN por barbeiro).
- Campanhas automáticas via WhatsApp (lista de clientes ociosos).
- Estoque de produtos (revender pomada/cosmético sai automaticamente do caixa).
- Metas por serviço, alertas proativos.
- Sincronização em nuvem quando for modelo de negócio replicável.
- Migração para UI mais robusta (PySide6) e DB cliente-servidor.

---

## 9. Migração da planilha atual

Script único `scripts/migrar_planilha.py`:

1. Lê `fluxo_caixa.xlsx` (aba MAR).
2. **Receitas**: cria registros diários consolidados usando o serviço legado "Fechamento diário" (criado só para a migração) com o valor total. O dono começa o detalhamento por serviço a partir da data da instalação.
3. **Despesas**: mapeia heuristicamente para categoria + item frequente (`lamina` → Insumos/Lâmina, `bala|café|coca|sprite` → Bebidas&Alimentos, `ferro das grades` → Manutenção, `mando no pix|vale` → Pessoal). Saída em CSV de log para revisão manual.
4. Corrige datas com ano/século inconsistentes (`1900-03-26`, `2025-*` → `2026-*`).
5. Assinaturas e clientes não vêm da planilha — são cadastrados manualmente pelo dono no 1º uso (fase educativa do projeto).

---

## 10. Métricas de sucesso do MVP

- Tempo médio de lançamento de atendimento: **< 5 s**; assinante: **< 3 s**.
- Zero erros de digitação de data em 30 dias.
- Dono consegue fechar o mês em **< 2 min** (vs. ~20 min na planilha).
- Backup recuperável testado ao menos 1× antes da entrega.
- 100% dos assinantes ativos cadastrados nas 2 primeiras semanas.
- Pelo menos 1 decisão de negócio (upsell, campanha, mudança de plano) tomada com base no relatório de assinantes no 1º mês.
- Dono aceita substituir a planilha após 14 dias de uso.

---

## 11. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| CustomTkinter travar em dashboards pesados | Matplotlib em thread separada + cache de queries agregadas. |
| Dono fechar o app sem salvar | Auto-commit a cada operação (SQLite é transacional). |
| Perda do arquivo .db | Backup automático + instruir cópia semanal pra Google Drive/pendrive. |
| Mudança de requisito (ex: voltar a multi-conta) | Arquitetura em camadas isola o impacto. |
| Dono resistir ao cadastro de clientes/assinantes | Fluxo "assinante com 1 clique" + o app calcular o ROI da base cadastrada (ex: "você só cadastrou 8 clientes e já identificou R$ 340 de upsell"). |
| Confusão entre atendimento de plano e avulso | UX separa em abas distintas + valor 0 visível + card do plano mostrando uso antes de confirmar. |

---

## 12. Próximos passos sugeridos

1. ✅ Plano revisado e confirmado pelo dono (17/04/26).
2. ✅ Catálogo de 37 serviços confirmado com preços atuais. Preços são editáveis em runtime — "4 Cortes R$ 112" é candidato a reajuste para R$ 105 no futuro.
3. ✅ 5 planos de assinatura confirmados. "Corte + Barba R$ 100" = ilimitado.
4. ✅ Categorias e itens frequentes de despesa validados (~80% de cobertura do dia-a-dia).
5. ▶ **Iniciar Fase 0** — estrutura de pastas, conexão SQLite, schema, seed e testes unitários mínimos.
