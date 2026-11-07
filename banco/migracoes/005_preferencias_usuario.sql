-- =====================================================================
-- ParkFlow - Migração 005: preferências de aparência salvas por usuário
-- Alvo: MariaDB 10.11. Só ADICIONA uma coluna; pode ser executada mais de uma vez.
-- Sem esta migração o sistema funciona: as preferências valem só durante a sessão.
-- Faça backup antes.
-- =====================================================================
ALTER TABLE usuarios
  ADD COLUMN IF NOT EXISTS preferencias JSON NULL;

SHOW COLUMNS FROM usuarios LIKE 'preferencias';
