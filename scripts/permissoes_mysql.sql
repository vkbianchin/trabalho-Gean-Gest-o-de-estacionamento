-- Execute manualmente com uma conta administrativa do MySQL.
-- Troque a senha e confirme o nome do banco antes de executar.
CREATE USER IF NOT EXISTS 'estacionamento_app'@'localhost' IDENTIFIED BY 'TROQUE_ESSA_SENHA';
GRANT SELECT, INSERT, UPDATE, DELETE ON estacionamento.* TO 'estacionamento_app'@'localhost';
-- A tabela de auditoria deve ser somente leitura e inserção para o usuário do app.
REVOKE UPDATE, DELETE ON estacionamento.auditoria FROM 'estacionamento_app'@'localhost';
GRANT SELECT, INSERT ON estacionamento.auditoria TO 'estacionamento_app'@'localhost';
FLUSH PRIVILEGES;
