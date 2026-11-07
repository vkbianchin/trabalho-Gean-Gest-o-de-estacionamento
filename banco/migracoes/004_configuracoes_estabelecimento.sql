-- =====================================================================
-- ParkFlow - Migração 004: dados do estabelecimento (recibo) e carência de atraso
--
-- Alvo: MariaDB 10.11. Só ADICIONA colunas em configuracoes; pode ser executada mais de uma vez.
--
-- Colunas novas:
--   razao_social, cnpj, endereco, telefone ......... aparecem no cabeçalho do recibo
--   dias_carencia_atraso ........................... dias depois do vencimento até a mensalidade
--                                                    contar como "em atraso" (0 = no dia seguinte)
--
-- Se esta migração não for aplicada, o sistema continua funcionando: apenas não grava esses campos.
-- Faça backup antes (MySQL Workbench: Server > Data Export).
-- =====================================================================

ALTER TABLE configuracoes
  ADD COLUMN IF NOT EXISTS razao_social         VARCHAR(150) NULL,
  ADD COLUMN IF NOT EXISTS cnpj                 CHAR(14) NULL,
  ADD COLUMN IF NOT EXISTS endereco             VARCHAR(200) NULL,
  ADD COLUMN IF NOT EXISTS telefone             VARCHAR(13) NULL,
  ADD COLUMN IF NOT EXISTS dias_carencia_atraso TINYINT UNSIGNED NOT NULL DEFAULT 0;

SHOW COLUMNS FROM configuracoes;
