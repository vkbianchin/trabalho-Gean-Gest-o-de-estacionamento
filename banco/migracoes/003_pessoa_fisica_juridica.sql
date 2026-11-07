-- =====================================================================
-- ParkFlow - Migração 003: clientes pessoa física ou jurídica (CPF ou CNPJ)
--
-- Alvo: MariaDB 10.11 (usa IF [NOT] EXISTS). Pode ser executada mais de uma vez.
--
-- O que faz:
--   1) adiciona clientes.tipo_pessoa ('fisica' ou 'juridica'; os atuais ficam 'fisica');
--   2) renomeia clientes.cpf para clientes.documento e amplia para 14 caracteres
--      (CPF = 11 dígitos, CNPJ = 14). O índice único continua valendo.
--
-- ORDEM IMPORTANTE: rode esta migração ANTES de colocar o código novo no ar.
-- O código novo lê e grava a coluna "documento"; sem a migração o cadastro de clientes falha.
-- Faça backup antes (MySQL Workbench: Server > Data Export).
-- =====================================================================

ALTER TABLE clientes
  ADD COLUMN IF NOT EXISTS tipo_pessoa ENUM('fisica','juridica') NOT NULL DEFAULT 'fisica' AFTER nome;

ALTER TABLE clientes
  CHANGE COLUMN IF EXISTS cpf documento VARCHAR(14) NOT NULL;

-- Conferência: deve listar a coluna "documento" e "tipo_pessoa".
SHOW COLUMNS FROM clientes;
