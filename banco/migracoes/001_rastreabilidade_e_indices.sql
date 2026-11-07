-- =====================================================================
-- ParkFlow - Migração 001 (RASCUNHO PARA REVISÃO - NÃO APLICADA)
-- Rastreabilidade de cancelamentos e retroativas + índices de consulta.
--
-- Alvo: MariaDB 10.11 (usa IF NOT EXISTS, que o MySQL 8 não aceita).
-- Só ADICIONA colunas, chaves e índices. Não apaga, não recria e não
-- altera dados. Pode ser executada mais de uma vez sem erro.
--
-- Antes de executar:
--   1. Faça backup (Server > Data Export no Workbench).
--   2. Rode 000_verificacoes_integridade.sql e confira o resultado.
--   3. Selecione o banco do projeto e execute com conta administrativa.
-- Efeito: as tabelas movimentacoes, pagamentos e caixas são reconstruídas
-- pelo servidor durante o ALTER (rápido em tabelas pequenas); evite
-- executar com operadores lançando entradas e saídas.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. MOVIMENTAÇÕES: quem cancelou, quando e por quê; justificativa da
--    entrada/saída retroativa (exigida só de administradores).
-- ---------------------------------------------------------------------
ALTER TABLE movimentacoes
  ADD COLUMN IF NOT EXISTS cancelada_por             INT NULL,
  ADD COLUMN IF NOT EXISTS cancelada_em              DATETIME NULL,
  ADD COLUMN IF NOT EXISTS motivo_cancelamento       VARCHAR(200) NULL,
  ADD COLUMN IF NOT EXISTS justificativa_retroativa  VARCHAR(200) NULL;

ALTER TABLE movimentacoes
  ADD CONSTRAINT fk_mov_cancelada_por
  FOREIGN KEY IF NOT EXISTS (cancelada_por) REFERENCES usuarios(id);

-- ---------------------------------------------------------------------
-- 2. PAGAMENTOS: mesmo rastro para o cancelamento de pagamento.
--    A linha cancelada continua existindo (histórico preservado).
-- ---------------------------------------------------------------------
ALTER TABLE pagamentos
  ADD COLUMN IF NOT EXISTS cancelado_por        INT NULL,
  ADD COLUMN IF NOT EXISTS cancelado_em         DATETIME NULL,
  ADD COLUMN IF NOT EXISTS motivo_cancelamento  VARCHAR(200) NULL;

ALTER TABLE pagamentos
  ADD CONSTRAINT fk_pag_cancelado_por
  FOREIGN KEY IF NOT EXISTS (cancelado_por) REFERENCES usuarios(id);

-- ---------------------------------------------------------------------
-- 3. ÍNDICES para relatórios e financeiro (filtros por período).
-- ---------------------------------------------------------------------
-- Recebimentos por dia/mês e por forma de pagamento:
CREATE INDEX IF NOT EXISTS idx_pagamentos_recebimento
  ON pagamentos (situacao, pago_em, forma_pagamento);

-- Saídas por período:
CREATE INDEX IF NOT EXISTS idx_movimentacoes_saida
  ON movimentacoes (saida_em);

-- Fechamentos de caixa por período:
CREATE INDEX IF NOT EXISTS idx_caixas_fechado_em
  ON caixas (fechado_em);

-- ---------------------------------------------------------------------
-- 4. CONFERÊNCIA (somente leitura): deve listar as colunas e índices novos.
-- ---------------------------------------------------------------------
SELECT table_name, column_name
  FROM information_schema.columns
 WHERE table_schema = DATABASE()
   AND ((table_name = 'movimentacoes' AND column_name IN
          ('cancelada_por','cancelada_em','motivo_cancelamento','justificativa_retroativa'))
     OR (table_name = 'pagamentos' AND column_name IN
          ('cancelado_por','cancelado_em','motivo_cancelamento')))
 ORDER BY table_name, column_name;

SELECT table_name, index_name
  FROM information_schema.statistics
 WHERE table_schema = DATABASE()
   AND index_name IN ('idx_pagamentos_recebimento','idx_movimentacoes_saida','idx_caixas_fechado_em')
 GROUP BY table_name, index_name;

-- ---------------------------------------------------------------------
-- COMO DESFAZER (somente se necessário; apaga apenas o que esta migração
-- criou, e os cancelamentos/justificativas gravados nessas colunas):
--   ALTER TABLE movimentacoes DROP FOREIGN KEY fk_mov_cancelada_por;
--   ALTER TABLE movimentacoes DROP COLUMN cancelada_por, DROP COLUMN cancelada_em,
--     DROP COLUMN motivo_cancelamento, DROP COLUMN justificativa_retroativa;
--   ALTER TABLE pagamentos DROP FOREIGN KEY fk_pag_cancelado_por;
--   ALTER TABLE pagamentos DROP COLUMN cancelado_por, DROP COLUMN cancelado_em,
--     DROP COLUMN motivo_cancelamento;
--   DROP INDEX idx_pagamentos_recebimento ON pagamentos;
--   DROP INDEX idx_movimentacoes_saida ON movimentacoes;
--   DROP INDEX idx_caixas_fechado_em ON caixas;
-- ---------------------------------------------------------------------
