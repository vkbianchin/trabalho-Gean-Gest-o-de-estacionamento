-- =====================================================================
-- ParkFlow - Estrutura completa do banco (estado após as migrações 000 a 006)
-- Alvo: MariaDB 10.11. Somente estrutura, sem dados.
--
-- COMO USAR
--   Instalação nova:    execute este arquivo inteiro no banco vazio e depois rode
--                       python -m scripts.criar_primeiro_usuario e python -m scripts.dados_iniciais.
--   Banco já existente: NÃO execute este arquivo; aplique as migrações de banco/migracoes/ em ordem.
--
-- ATENÇÃO: este arquivo foi RECONSTRUÍDO a partir do código (consultas SQL e migrações), não
-- exportado do banco. Trechos marcados com [CONFERIR] são deduções. Para gerar a versão oficial:
--     python -m scripts.exportar_schema      (usa o mysqldump e o .env do projeto)
-- e compare com este arquivo antes de confiar nele em produção. Não foi executado em um servidor.
-- =====================================================================

SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS usuarios (
  id               INT NOT NULL AUTO_INCREMENT,
  nome             VARCHAR(100) NOT NULL,
  email            VARCHAR(150) NOT NULL,
  login            VARCHAR(50)  NOT NULL,
  senha_hash       VARCHAR(100) NOT NULL,                     -- bcrypt
  nivel_acesso     ENUM('administrador','operador') NOT NULL,
  trocar_senha     TINYINT(1) NOT NULL DEFAULT 1,
  ativo            TINYINT(1) NOT NULL DEFAULT 1,
  tentativas_login SMALLINT UNSIGNED NOT NULL DEFAULT 0,      -- migração 002
  preferencias     JSON NULL,                                 -- migração 005
  totp_segredo     VARCHAR(64) NULL,                          -- migração 006
  totp_ativo       TINYINT(1) NOT NULL DEFAULT 0,             -- migração 006
  bloqueado_ate    DATETIME NULL,                             -- migração 002
  criado_em        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em    DATETIME NULL ON UPDATE CURRENT_TIMESTAMP,
  criado_por       INT NULL,
  atualizado_por   INT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_usuarios_login (login),
  UNIQUE KEY uq_usuarios_email (email),
  CONSTRAINT fk_usuarios_criado_por    FOREIGN KEY (criado_por)    REFERENCES usuarios(id),
  CONSTRAINT fk_usuarios_atualizado_por FOREIGN KEY (atualizado_por) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS clientes (
  id             INT NOT NULL AUTO_INCREMENT,
  nome           VARCHAR(100) NOT NULL,                       -- nome da pessoa ou razão social
  tipo_pessoa    ENUM('fisica','juridica') NOT NULL DEFAULT 'fisica',   -- migração 003
  documento      VARCHAR(14) NOT NULL,                        -- CPF (11) ou CNPJ (14), só dígitos; migração 003
  telefone       VARCHAR(13) NOT NULL,
  email          VARCHAR(150) NULL,
  cep            CHAR(8) NOT NULL,
  logradouro     VARCHAR(150) NOT NULL,
  numero         VARCHAR(10) NOT NULL,
  complemento    VARCHAR(60) NULL,
  bairro         VARCHAR(80) NOT NULL,
  cidade         VARCHAR(80) NOT NULL,
  uf             CHAR(2) NOT NULL,
  ativo          TINYINT(1) NOT NULL DEFAULT 1,
  criado_em      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em  DATETIME NULL ON UPDATE CURRENT_TIMESTAMP,
  criado_por     INT NULL,
  atualizado_por INT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_clientes_documento (documento),
  CONSTRAINT fk_clientes_criado_por FOREIGN KEY (criado_por) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Catálogos ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS tipos_veiculo (                    -- Carro, Moto
  id INT NOT NULL AUTO_INCREMENT,
  nome VARCHAR(60) NOT NULL,
  ativo TINYINT(1) NOT NULL DEFAULT 1,                        -- [CONFERIR]
  criado_por INT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_tipos_veiculo_nome (nome),
  CONSTRAINT fk_tipos_criado_por FOREIGN KEY (criado_por) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS marcas (
  id INT NOT NULL AUTO_INCREMENT,
  nome VARCHAR(60) NOT NULL,
  ativo TINYINT(1) NOT NULL DEFAULT 1,                        -- [CONFERIR]
  criado_por INT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_marcas_nome (nome),
  CONSTRAINT fk_marcas_criado_por FOREIGN KEY (criado_por) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS modelos (
  id INT NOT NULL AUTO_INCREMENT,
  nome VARCHAR(60) NOT NULL,
  tipo_veiculo_id INT NOT NULL,
  marca_id INT NOT NULL,                                      -- [CONFERIR] pode ser opcional no banco real
  ativo TINYINT(1) NOT NULL DEFAULT 1,
  criado_por INT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_modelos (nome, tipo_veiculo_id, marca_id),
  CONSTRAINT fk_modelos_tipo  FOREIGN KEY (tipo_veiculo_id) REFERENCES tipos_veiculo(id),
  CONSTRAINT fk_modelos_marca FOREIGN KEY (marca_id)        REFERENCES marcas(id),
  CONSTRAINT fk_modelos_criado_por FOREIGN KEY (criado_por) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS cores (
  id INT NOT NULL AUTO_INCREMENT,
  nome VARCHAR(60) NOT NULL,
  ativo TINYINT(1) NOT NULL DEFAULT 1,                        -- [CONFERIR]
  criado_por INT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_cores_nome (nome),
  CONSTRAINT fk_cores_criado_por FOREIGN KEY (criado_por) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS planos (                           -- Horista (hora), Mensalista (mensal)
  id INT NOT NULL AUTO_INCREMENT,
  nome VARCHAR(30) NOT NULL,
  cobranca ENUM('mensal','hora') NOT NULL,
  ativo TINYINT(1) NOT NULL DEFAULT 1,
  criado_por INT NULL,
  atualizado_por INT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_planos_nome (nome),
  CONSTRAINT fk_planos_criado_por FOREIGN KEY (criado_por) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS precos (                           -- preço por plano + tipo de veículo
  id INT NOT NULL AUTO_INCREMENT,
  plano_id INT NOT NULL,
  tipo_veiculo_id INT NOT NULL,
  valor DECIMAL(10,2) NOT NULL,                               -- valor da hora [CONFERIR precisão]
  valor_diaria DECIMAL(10,2) NULL,
  criado_por INT NULL,
  atualizado_por INT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_precos_plano_tipo (plano_id, tipo_veiculo_id),
  CONSTRAINT fk_precos_plano FOREIGN KEY (plano_id) REFERENCES planos(id),
  CONSTRAINT fk_precos_tipo  FOREIGN KEY (tipo_veiculo_id) REFERENCES tipos_veiculo(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS configuracoes (                    -- uma única linha (id = 1)
  id INT NOT NULL,
  nome_estacionamento VARCHAR(80) NOT NULL,
  tolerancia_minutos INT NOT NULL DEFAULT 10,
  arredondamento ENUM('hora_cheia','fracao') NOT NULL DEFAULT 'fracao',
  fracao_minutos INT NOT NULL DEFAULT 30,
  razao_social VARCHAR(150) NULL,                             -- migração 004
  cnpj CHAR(14) NULL,                                         -- migração 004
  endereco VARCHAR(200) NULL,                                 -- migração 004
  telefone VARCHAR(13) NULL,                                  -- migração 004
  dias_carencia_atraso TINYINT UNSIGNED NOT NULL DEFAULT 0,   -- migração 004
  criado_por INT NULL,
  atualizado_por INT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS vagas (
  id INT NOT NULL AUTO_INCREMENT,
  numero INT NOT NULL,
  tipo_veiculo_id INT NOT NULL,
  plano_id INT NOT NULL,
  ativo TINYINT(1) NOT NULL DEFAULT 1,
  criado_por INT NULL,
  atualizado_por INT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_vagas_numero (numero),
  CONSTRAINT fk_vagas_tipo  FOREIGN KEY (tipo_veiculo_id) REFERENCES tipos_veiculo(id),
  CONSTRAINT fk_vagas_plano FOREIGN KEY (plano_id)        REFERENCES planos(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS veiculos (
  id INT NOT NULL AUTO_INCREMENT,
  cliente_id INT NOT NULL,
  tipo_veiculo_id INT NOT NULL,
  placa CHAR(7) NOT NULL,                                     -- sem hífen, maiúscula
  modelo_id INT NULL,
  cor_id INT NULL,
  ativo TINYINT(1) NOT NULL DEFAULT 1,
  criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  criado_por INT NULL,
  atualizado_por INT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_veiculos_placa (placa),
  CONSTRAINT fk_veiculos_cliente FOREIGN KEY (cliente_id)      REFERENCES clientes(id),
  CONSTRAINT fk_veiculos_tipo    FOREIGN KEY (tipo_veiculo_id) REFERENCES tipos_veiculo(id),
  CONSTRAINT fk_veiculos_modelo  FOREIGN KEY (modelo_id)       REFERENCES modelos(id),
  CONSTRAINT fk_veiculos_cor     FOREIGN KEY (cor_id)          REFERENCES cores(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS contratos_mensalistas (
  id INT NOT NULL AUTO_INCREMENT,
  cliente_id INT NOT NULL,
  veiculo_id INT NOT NULL,
  valor_mensal DECIMAL(10,2) NOT NULL,
  dia_vencimento TINYINT UNSIGNED NOT NULL,                   -- 1 a 28
  data_inicio DATE NOT NULL,
  data_fim DATE NULL,
  motivo_encerramento ENUM('cancelado_cliente','inadimplencia','troca_veiculo','outro') NULL,
  criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  criado_por INT NULL,
  atualizado_por INT NULL,
  -- [CONFERIR] o código trata erro 1062 como "veículo já tem contrato vigente":
  -- provável índice único que só vale enquanto data_fim é NULL.
  veiculo_vigente INT GENERATED ALWAYS AS (IF(data_fim IS NULL, veiculo_id, NULL)) STORED,
  PRIMARY KEY (id),
  UNIQUE KEY uq_contrato_vigente_veiculo (veiculo_vigente),
  CONSTRAINT fk_contratos_cliente FOREIGN KEY (cliente_id) REFERENCES clientes(id),
  CONSTRAINT fk_contratos_veiculo FOREIGN KEY (veiculo_id) REFERENCES veiculos(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS caixas (
  id INT NOT NULL AUTO_INCREMENT,
  usuario_id INT NOT NULL,
  aberto_em DATETIME NOT NULL,
  fechado_em DATETIME NULL,
  valor_inicial DECIMAL(10,2) NOT NULL DEFAULT 0,
  dinheiro_esperado DECIMAL(10,2) NULL,
  dinheiro_contado DECIMAL(10,2) NULL,
  diferenca DECIMAL(10,2) NULL,
  observacao VARCHAR(255) NULL,
  criado_por INT NULL,
  atualizado_por INT NULL,
  PRIMARY KEY (id),
  KEY idx_caixas_fechado_em (fechado_em),                     -- migração 001
  CONSTRAINT fk_caixas_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS movimentacoes (
  id INT NOT NULL AUTO_INCREMENT,
  vaga_id INT NOT NULL,
  plano_id INT NOT NULL,
  tipo_veiculo_id INT NOT NULL,
  placa CHAR(7) NOT NULL,
  veiculo_id INT NULL,                                        -- só mensalista
  contrato_id INT NULL,                                       -- só mensalista
  entrada_em DATETIME NOT NULL,
  saida_em DATETIME NULL,
  valor_cobrado DECIMAL(10,2) NULL,
  retroativa TINYINT(1) NOT NULL DEFAULT 0,
  cancelada TINYINT(1) NOT NULL DEFAULT 0,
  criado_por INT NULL,
  atualizado_por INT NULL,
  cancelada_por INT NULL,                                     -- migração 001
  cancelada_em DATETIME NULL,                                 -- migração 001
  motivo_cancelamento VARCHAR(200) NULL,                      -- migração 001
  justificativa_retroativa VARCHAR(200) NULL,                 -- migração 001
  -- [CONFERIR] "aberta" e os índices únicos abaixo são dedução: o código lê
  -- m.aberta e trata erro 1062 como "vaga ou placa já ocupada".
  aberta TINYINT(1) GENERATED ALWAYS AS (saida_em IS NULL AND cancelada = 0) STORED,
  placa_aberta CHAR(7) GENERATED ALWAYS AS (IF(saida_em IS NULL AND cancelada = 0, placa, NULL)) STORED,
  vaga_aberta  INT     GENERATED ALWAYS AS (IF(saida_em IS NULL AND cancelada = 0, vaga_id, NULL)) STORED,
  PRIMARY KEY (id),
  UNIQUE KEY uq_mov_placa_aberta (placa_aberta),
  UNIQUE KEY uq_mov_vaga_aberta (vaga_aberta),
  KEY idx_movimentacoes_saida (saida_em),                     -- migração 001
  KEY idx_movimentacoes_placa (placa),
  CONSTRAINT fk_mov_vaga     FOREIGN KEY (vaga_id)         REFERENCES vagas(id),
  CONSTRAINT fk_mov_plano    FOREIGN KEY (plano_id)        REFERENCES planos(id),
  CONSTRAINT fk_mov_tipo     FOREIGN KEY (tipo_veiculo_id) REFERENCES tipos_veiculo(id),
  CONSTRAINT fk_mov_veiculo  FOREIGN KEY (veiculo_id)      REFERENCES veiculos(id),
  CONSTRAINT fk_mov_contrato FOREIGN KEY (contrato_id)     REFERENCES contratos_mensalistas(id),
  CONSTRAINT fk_mov_cancelada_por FOREIGN KEY (cancelada_por) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS pagamentos (
  id INT NOT NULL AUTO_INCREMENT,
  movimentacao_id INT NULL,                                   -- pagamento de horista
  contrato_id INT NULL,                                       -- mensalidade
  competencia DATE NULL,                                      -- sempre dia 1 do mês (mensalidade)
  vencimento DATE NULL,
  valor DECIMAL(10,2) NOT NULL,
  situacao ENUM('aberto','pago','cancelado') NOT NULL DEFAULT 'aberto',
  forma_pagamento ENUM('dinheiro','pix','cartao_debito','cartao_credito') NULL,
  pago_em DATETIME NULL,
  caixa_id INT NULL,
  criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  criado_por INT NULL,
  atualizado_por INT NULL,
  cancelado_por INT NULL,                                     -- migração 001
  cancelado_em DATETIME NULL,                                 -- migração 001
  motivo_cancelamento VARCHAR(200) NULL,                      -- migração 001
  -- [CONFERIR] o código trata erro 1062 ao gerar mensalidade repetida:
  -- provável unicidade de (contrato_id, competencia) ignorando canceladas.
  PRIMARY KEY (id),
  KEY idx_pagamentos_recebimento (situacao, pago_em, forma_pagamento),  -- migração 001
  KEY idx_pagamentos_contrato (contrato_id, competencia),
  CONSTRAINT fk_pag_mov      FOREIGN KEY (movimentacao_id) REFERENCES movimentacoes(id),
  CONSTRAINT fk_pag_contrato FOREIGN KEY (contrato_id)     REFERENCES contratos_mensalistas(id),
  CONSTRAINT fk_pag_caixa    FOREIGN KEY (caixa_id)        REFERENCES caixas(id),
  CONSTRAINT fk_pag_cancelado_por FOREIGN KEY (cancelado_por) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS auditoria (                        -- só INSERT e SELECT para o usuário do app
  id INT NOT NULL AUTO_INCREMENT,
  tabela VARCHAR(60) NOT NULL,
  registro_id INT NOT NULL,
  acao VARCHAR(30) NOT NULL,                                  -- criou, alterou ...
  usuario_id INT NOT NULL,
  data_hora DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  dados_antes JSON NULL,
  dados_depois JSON NULL,
  PRIMARY KEY (id),
  KEY idx_auditoria_data (data_hora),
  KEY idx_auditoria_registro (tabela, registro_id),
  CONSTRAINT fk_auditoria_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
