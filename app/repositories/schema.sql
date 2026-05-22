-- ============================================================================
-- Fluxo Barber — Schema SQLite
-- Valores monetários em CENTAVOS (INTEGER). Datas em ISO-8601 (YYYY-MM-DD).
-- Idempotente: pode ser re-executado em DB existente sem erro.
-- ============================================================================

-- ------------------------------------------------------------ 3.1 SERVIÇOS --
CREATE TABLE IF NOT EXISTS servico (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    nome              TEXT    NOT NULL UNIQUE,
    preco_padrao      INTEGER NOT NULL CHECK (preco_padrao >= 0),   -- centavos
    ativo             INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
    ordem             INTEGER NOT NULL DEFAULT 999,
    categoria_servico TEXT,  -- 'Corte' | 'Barba' | 'Combo' | 'Coloração' | 'Tratamento' | 'Penteado' | 'Prótese' | 'Estética'
    criado_em         TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_servico_ativo_ordem ON servico(ativo, ordem);

-- ----------------------------------------------- 3.2 PLANOS DE ASSINATURA --
CREATE TABLE IF NOT EXISTS plano_assinatura (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    nome             TEXT    NOT NULL UNIQUE,
    descricao        TEXT,
    preco_mensal     INTEGER NOT NULL CHECK (preco_mensal >= 0),    -- centavos
    qtd_servicos_mes INTEGER CHECK (qtd_servicos_mes IS NULL OR qtd_servicos_mes > 0),  -- NULL = ilimitado
    ativo            INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
    criado_em        TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Serviços cobertos por cada plano (N:N)
CREATE TABLE IF NOT EXISTS plano_servico (
    plano_id   INTEGER NOT NULL REFERENCES plano_assinatura(id) ON DELETE CASCADE,
    servico_id INTEGER NOT NULL REFERENCES servico(id),
    PRIMARY KEY (plano_id, servico_id)
);

-- ------------------------------------------------------------ 3.3 CLIENTE --
CREATE TABLE IF NOT EXISTS cliente (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT    NOT NULL,
    telefone    TEXT,
    aniversario TEXT,  -- YYYY-MM-DD opcional
    observacao  TEXT,
    criado_em   TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_cliente_nome ON cliente(nome);

-- --------------------------------------------------------- 3.4 ASSINATURA --
CREATE TABLE IF NOT EXISTS assinatura (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id    INTEGER NOT NULL REFERENCES cliente(id),
    plano_id      INTEGER NOT NULL REFERENCES plano_assinatura(id),
    data_inicio   TEXT    NOT NULL,            -- YYYY-MM-DD
    data_fim      TEXT,                        -- NULL = ativa
    dia_cobranca  INTEGER NOT NULL DEFAULT 1 CHECK (dia_cobranca BETWEEN 1 AND 28),
    criado_em     TEXT    NOT NULL DEFAULT (datetime('now')),
    CHECK (data_fim IS NULL OR data_fim >= data_inicio)
);
CREATE INDEX IF NOT EXISTS idx_assinatura_cliente ON assinatura(cliente_id);
CREATE INDEX IF NOT EXISTS idx_assinatura_ativa   ON assinatura(data_fim);

-- ------------------------------------------ 3.5 PAGAMENTO DE MENSALIDADE --
CREATE TABLE IF NOT EXISTS pagamento_assinatura (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    assinatura_id   INTEGER NOT NULL REFERENCES assinatura(id),
    mes_referencia  TEXT    NOT NULL,           -- YYYY-MM
    data_pagamento  TEXT    NOT NULL,
    valor           INTEGER NOT NULL CHECK (valor > 0),
    forma_pagamento TEXT    NOT NULL CHECK (forma_pagamento IN ('PIX', 'DINHEIRO', 'MAQUININHA')),
    criado_em       TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (assinatura_id, mes_referencia)       -- evita cobrança duplicada do mesmo mês
);
CREATE INDEX IF NOT EXISTS idx_pgto_assinatura_mes ON pagamento_assinatura(mes_referencia);

-- ------------------------------------------------------------ 3.6 RECEITA --
-- Colunas de sync (uuid + updated_at) existem para que a rotina de
-- sincronização com o BigQuery possa enviar apenas o delta e usar o
-- uuid como chave do MERGE (globalmente único entre instalações).
CREATE TABLE IF NOT EXISTS receita (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid             TEXT    UNIQUE,             -- chave global, populada no insert
    data             TEXT    NOT NULL,           -- YYYY-MM-DD
    servico_id       INTEGER NOT NULL REFERENCES servico(id),
    cliente_id       INTEGER          REFERENCES cliente(id),      -- NULL = anônimo
    assinatura_id    INTEGER          REFERENCES assinatura(id),   -- NOT NULL quando coberto por plano
    valor            INTEGER NOT NULL CHECK (valor >= 0),           -- 0 se coberto 100% pelo plano
    forma_pagamento  TEXT CHECK (forma_pagamento IS NULL OR forma_pagamento IN ('PIX', 'DINHEIRO', 'MAQUININHA')),
    observacao       TEXT,
    criado_em        TEXT    NOT NULL DEFAULT (datetime('now')),
    editado_em       TEXT,
    updated_at       TEXT    NOT NULL DEFAULT (datetime('now')),    -- atualizado em INSERT/UPDATE
    -- Integridade cruzada:
    -- 1) Se valor > 0, a forma de pagamento é obrigatória.
    -- 2) Se a receita é coberta por plano, precisa ter cliente.
    CHECK (valor = 0 OR forma_pagamento IS NOT NULL),
    CHECK (assinatura_id IS NULL OR cliente_id IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS idx_receita_data        ON receita(data);
CREATE INDEX IF NOT EXISTS idx_receita_cliente     ON receita(cliente_id);
CREATE INDEX IF NOT EXISTS idx_receita_assinatura  ON receita(assinatura_id);
CREATE INDEX IF NOT EXISTS idx_receita_updated_at  ON receita(updated_at);

-- ----------------------------------------------- 3.7 CATEGORIA DE DESPESA --
CREATE TABLE IF NOT EXISTS categoria_despesa (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    nome  TEXT    NOT NULL UNIQUE,
    icone TEXT,
    ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1))
);

-- ---------------------------------------- 3.8 ITEM FREQUENTE DE DESPESA --
CREATE TABLE IF NOT EXISTS item_despesa_frequente (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    descricao      TEXT    NOT NULL UNIQUE,
    categoria_id   INTEGER NOT NULL REFERENCES categoria_despesa(id),
    valor_sugerido INTEGER CHECK (valor_sugerido IS NULL OR valor_sugerido > 0),  -- centavos, opcional
    vezes_usado    INTEGER NOT NULL DEFAULT 0,
    ativo          INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1))
);
CREATE INDEX IF NOT EXISTS idx_item_freq_uso ON item_despesa_frequente(ativo, vezes_usado DESC);

-- ------------------------------------------------------------ 3.9 DESPESA --
CREATE TABLE IF NOT EXISTS despesa (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid              TEXT    UNIQUE,            -- chave global para sync
    data              TEXT    NOT NULL,
    categoria_id      INTEGER NOT NULL REFERENCES categoria_despesa(id),
    item_frequente_id INTEGER          REFERENCES item_despesa_frequente(id),
    descricao         TEXT    NOT NULL,
    valor             INTEGER NOT NULL CHECK (valor > 0),
    forma_pagamento   TEXT    NOT NULL CHECK (forma_pagamento IN ('PIX', 'DINHEIRO', 'MAQUININHA')),
    criado_em         TEXT    NOT NULL DEFAULT (datetime('now')),
    editado_em        TEXT,
    updated_at        TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_despesa_data       ON despesa(data);
CREATE INDEX IF NOT EXISTS idx_despesa_categoria  ON despesa(categoria_id);
CREATE INDEX IF NOT EXISTS idx_despesa_updated_at ON despesa(updated_at);

-- ---------------------------------------------------------- 3.10 AUDITORIA --
CREATE TABLE IF NOT EXISTS auditoria (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    tabela       TEXT    NOT NULL,
    registro_id  INTEGER NOT NULL,
    acao         TEXT    NOT NULL CHECK (acao IN ('INSERT', 'UPDATE', 'DELETE')),
    payload      TEXT    NOT NULL,  -- JSON do estado antes/depois
    timestamp    TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_auditoria_tabela_registro ON auditoria(tabela, registro_id);

-- ------------------------------------------------------------ 3.11 CONFIG --
CREATE TABLE IF NOT EXISTS config (
    chave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);

-- ------------------------------------------------------------- 3.12 PRODUTO --
CREATE TABLE IF NOT EXISTS produto (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    nome              TEXT    NOT NULL UNIQUE,
    descricao         TEXT,
    preco_custo       INTEGER NOT NULL CHECK (preco_custo >= 0),   -- centavos
    preco_venda       INTEGER NOT NULL CHECK (preco_venda >= 0),   -- centavos
    quantidade_estoque INTEGER NOT NULL DEFAULT 0,
    ativo             INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
    criado_em         TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_produto_ativo ON produto(ativo);

-- ------------------------------------------------------- 3.13 MOVIMENTAÇÃO --
CREATE TABLE IF NOT EXISTS movimentacao_estoque (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id      INTEGER NOT NULL REFERENCES produto(id),
    tipo            TEXT    NOT NULL CHECK (tipo IN ('COMPRA', 'VENDA', 'AJUSTE')),
    quantidade      INTEGER NOT NULL CHECK (quantidade != 0),
    preco_unitario  INTEGER NOT NULL CHECK (preco_unitario >= 0),  -- centavos
    total_centavos  INTEGER NOT NULL,
    data            TEXT    NOT NULL,                              -- YYYY-MM-DD
    observacao      TEXT,
    criado_em       TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_mov_produto   ON movimentacao_estoque(produto_id);
CREATE INDEX IF NOT EXISTS idx_mov_data      ON movimentacao_estoque(data);
CREATE INDEX IF NOT EXISTS idx_mov_tipo      ON movimentacao_estoque(tipo);
