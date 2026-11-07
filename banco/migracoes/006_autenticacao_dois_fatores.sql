-- =====================================================================
-- ParkFlow - Migração 006: verificação em duas etapas (TOTP)
-- Alvo: MariaDB 10.11. Só ADICIONA colunas; pode ser executada mais de uma vez.
-- Sem esta migração o sistema funciona normalmente, apenas sem a opção de 2FA.
--
-- totp_segredo ... segredo Base32 do aplicativo autenticador (fica em texto no banco:
--                  proteja o acesso ao banco e os backups).
-- totp_ativo ..... 1 quando o usuário concluiu a configuração.
-- Faça backup antes.
-- =====================================================================
ALTER TABLE usuarios
  ADD COLUMN IF NOT EXISTS totp_segredo VARCHAR(64) NULL,
  ADD COLUMN IF NOT EXISTS totp_ativo   TINYINT(1) NOT NULL DEFAULT 0;

SHOW COLUMNS FROM usuarios LIKE 'totp%';
