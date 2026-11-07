-- =====================================================================
-- ParkFlow - Migração 002 (RASCUNHO PARA REVISÃO - NÃO APLICADA)
-- Limitação temporária de tentativas de login (parte 2.A).
--
-- Alvo: MariaDB 10.11. Só ADICIONA duas colunas em usuarios.
-- Os usuários atuais ficam com tentativas_login = 0 e sem bloqueio.
-- Pode ser executada mais de uma vez sem erro.
--
-- ORDEM IMPORTANTE: rode esta migração ANTES de copiar os arquivos novos
-- do projeto. O código novo consulta estas colunas; sem elas o login falha.
--
-- Antes de executar: backup (Server > Data Export) e banco do projeto
-- selecionado, com a conta administrativa do Workbench.
-- =====================================================================

ALTER TABLE usuarios
  ADD COLUMN IF NOT EXISTS tentativas_login  SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS bloqueado_ate     DATETIME NULL;

-- Conferência (somente leitura): deve listar as 2 colunas.
SELECT column_name, column_type, is_nullable, column_default
  FROM information_schema.columns
 WHERE table_schema = DATABASE()
   AND table_name = 'usuarios'
   AND column_name IN ('tentativas_login', 'bloqueado_ate');

-- COMO DESFAZER (apaga só o que esta migração criou):
--   ALTER TABLE usuarios DROP COLUMN tentativas_login, DROP COLUMN bloqueado_ate;
