-- Schema da fatia executável — PostgreSQL (alvo de produção, ADR-0002)
-- Cada tabela cita a ADR que a exige.

CREATE TABLE IF NOT EXISTS pedido (
    id            TEXT PRIMARY KEY,
    cliente_id    TEXT NOT NULL,
    canal         TEXT NOT NULL,
    status        TEXT NOT NULL,          -- RECEBIDO | CONFIRMADO | REJEITADO
    criado_em     TEXT NOT NULL,
    atualizado_em TEXT NOT NULL
);

-- ADR-0003: snapshot imutável dos termos acordados.
-- As colunas de snapshot são NOT NULL de propósito: a constraint É a garantia.
CREATE TABLE IF NOT EXISTS pedido_item (
    id              BIGSERIAL PRIMARY KEY,
    pedido_id       TEXT    NOT NULL REFERENCES pedido(id),
    sku             TEXT    NOT NULL,
    quantidade      REAL    NOT NULL,
    descricao       TEXT    NOT NULL,     -- snapshot
    preco_unitario  BIGINT  NOT NULL,     -- snapshot, em centavos (nunca float)
    moeda           TEXT    NOT NULL,     -- snapshot
    unidade         TEXT    NOT NULL,     -- snapshot: "quantidade 2" não significa nada sem isto
    peso_gramas     BIGINT  NOT NULL,     -- snapshot: base do frete cotado
    promocao_id     TEXT,                 -- snapshot, opcional
    catalogo_versao TEXT    NOT NULL      -- evidência de auditoria
);

-- ADR-0001: a garantia de idempotência depende desta PRIMARY KEY, não do código.
CREATE TABLE IF NOT EXISTS idempotency_key (
    chamador     TEXT NOT NULL,
    chave        TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    pedido_id    TEXT NOT NULL,
    criado_em    TEXT NOT NULL,
    expira_em    TEXT NOT NULL,
    PRIMARY KEY (chamador, chave)
);

-- ADR-0002: outbox na MESMA base, gravado na MESMA transação do pedido.
CREATE TABLE IF NOT EXISTS outbox (
    id             BIGSERIAL PRIMARY KEY,
    event_id       TEXT NOT NULL UNIQUE,
    tipo           TEXT NOT NULL,
    versao         TEXT NOT NULL,
    chave_particao TEXT NOT NULL,         -- pedido_id: ordenação por agregado
    payload        TEXT NOT NULL,
    criado_em      TEXT NOT NULL,
    publicado_em   TEXT                   -- NULL = pendente
);

CREATE INDEX IF NOT EXISTS idx_outbox_pendente
    ON outbox(id) WHERE publicado_em IS NULL;
