-- =====================================================================
-- ParkFlow - Verificações de integridade (SOMENTE LEITURA)
-- Alvo: MariaDB 10.11. Não altera nada: só faz SELECT.
--
-- Como usar (MySQL Workbench):
--   1. Selecione o banco do projeto (duplo clique nele no painel SCHEMAS).
--   2. Abra este arquivo e execute tudo (raio ou Ctrl+Shift+Enter).
--   3. Envie o resultado (uma única tabela com duas colunas).
--
-- Leitura do resultado:
--   [deve ser 0]   -> qualquer valor maior que 0 é inconsistência nos dados.
--   [informativo]  -> só contagem, para conhecermos o volume atual.
-- =====================================================================

SELECT '[deve ser 0] pagamentos pagos sem caixa' AS verificacao, COUNT(*) AS quantidade
  FROM pagamentos WHERE situacao = 'pago' AND caixa_id IS NULL
UNION ALL
SELECT '[deve ser 0] mensalidades com competência fora do dia 1', COUNT(*)
  FROM pagamentos WHERE contrato_id IS NOT NULL AND DAY(competencia) <> 1
UNION ALL
SELECT '[deve ser 0] mensalidades com vencimento fora do mês da competência', COUNT(*)
  FROM pagamentos
 WHERE contrato_id IS NOT NULL
   AND DATE_FORMAT(vencimento, '%Y-%m') <> DATE_FORMAT(competencia, '%Y-%m')
UNION ALL
SELECT '[deve ser 0] mensalidades válidas fora da vigência do contrato', COUNT(*)
  FROM pagamentos p
  JOIN contratos_mensalistas c ON c.id = p.contrato_id
 WHERE p.situacao <> 'cancelado'
   AND (p.competencia < DATE_FORMAT(c.data_inicio, '%Y-%m-01')
        OR (c.data_fim IS NOT NULL AND p.competencia > c.data_fim))
UNION ALL
SELECT '[deve ser 0] movimentações encerradas sem valor cobrado', COUNT(*)
  FROM movimentacoes
 WHERE saida_em IS NOT NULL AND cancelada = 0 AND valor_cobrado IS NULL
UNION ALL
SELECT '[deve ser 0] horista com valor cobrado > 0 e sem pagamento válido', COUNT(*)
  FROM movimentacoes m
  JOIN planos pl ON pl.id = m.plano_id
  LEFT JOIN pagamentos p ON p.movimentacao_id = m.id AND p.situacao <> 'cancelado'
 WHERE pl.cobranca = 'hora' AND m.saida_em IS NOT NULL AND m.cancelada = 0
   AND m.valor_cobrado > 0 AND p.id IS NULL
UNION ALL
SELECT '[deve ser 0] pagamento de horista com valor diferente do cobrado', COUNT(*)
  FROM pagamentos p
  JOIN movimentacoes m ON m.id = p.movimentacao_id
 WHERE p.situacao <> 'cancelado' AND p.valor <> m.valor_cobrado
UNION ALL
SELECT '[deve ser 0] pagamento válido ligado a movimentação cancelada', COUNT(*)
  FROM pagamentos p
  JOIN movimentacoes m ON m.id = p.movimentacao_id
 WHERE p.situacao <> 'cancelado' AND m.cancelada = 1
UNION ALL
SELECT '[deve ser 0] movimentação com veículo e contrato incoerentes (só um preenchido)', COUNT(*)
  FROM movimentacoes WHERE (veiculo_id IS NULL) <> (contrato_id IS NULL)
UNION ALL
SELECT '[deve ser 0] movimentação com placa diferente da placa do veículo', COUNT(*)
  FROM movimentacoes m JOIN veiculos v ON v.id = m.veiculo_id WHERE m.placa <> v.placa
UNION ALL
SELECT '[deve ser 0] movimentação cujo contrato é de outro veículo', COUNT(*)
  FROM movimentacoes m JOIN contratos_mensalistas c ON c.id = m.contrato_id
 WHERE c.veiculo_id <> m.veiculo_id
UNION ALL
SELECT '[deve ser 0] plano da movimentação incompatível com contrato', COUNT(*)
  FROM movimentacoes m JOIN planos pl ON pl.id = m.plano_id
 WHERE (pl.cobranca = 'mensal' AND m.contrato_id IS NULL)
    OR (pl.cobranca = 'hora' AND m.contrato_id IS NOT NULL)
UNION ALL
SELECT '[deve ser 0] tipo de veículo da movimentação diferente do tipo da vaga', COUNT(*)
  FROM movimentacoes m JOIN vagas g ON g.id = m.vaga_id
 WHERE g.tipo_veiculo_id <> m.tipo_veiculo_id
UNION ALL
SELECT '[deve ser 0] contrato de cliente diferente do dono do veículo', COUNT(*)
  FROM contratos_mensalistas c JOIN veiculos v ON v.id = c.veiculo_id
 WHERE c.cliente_id <> v.cliente_id
UNION ALL
SELECT '[deve ser 0] contratos vigentes com veículo ou cliente inativo', COUNT(*)
  FROM contratos_mensalistas c
  JOIN veiculos v ON v.id = c.veiculo_id
  JOIN clientes cl ON cl.id = c.cliente_id
 WHERE c.data_fim IS NULL AND (v.ativo = 0 OR cl.ativo = 0)
UNION ALL
SELECT '[deve ser 0] tipos de veículo com mais contratos vigentes do que vagas mensais ativas', COUNT(*)
  FROM (SELECT t.id,
               (SELECT COUNT(*) FROM contratos_mensalistas c
                  JOIN veiculos v ON v.id = c.veiculo_id
                 WHERE c.data_fim IS NULL AND v.tipo_veiculo_id = t.id) AS contratos,
               (SELECT COUNT(*) FROM vagas g JOIN planos p ON p.id = g.plano_id
                 WHERE g.ativo = 1 AND p.cobranca = 'mensal' AND g.tipo_veiculo_id = t.id) AS vagas
          FROM tipos_veiculo t) x
 WHERE x.contratos > x.vagas
UNION ALL
SELECT '[deve ser 0] caixas fechados com diferença inconsistente', COUNT(*)
  FROM caixas
 WHERE fechado_em IS NOT NULL AND diferenca <> dinheiro_contado - dinheiro_esperado
UNION ALL
SELECT '[deve ser 0] caixas fechados com dinheiro esperado diferente do recalculado', COUNT(*)
  FROM caixas c
 WHERE c.fechado_em IS NOT NULL
   AND c.dinheiro_esperado <> c.valor_inicial +
       (SELECT COALESCE(SUM(p.valor), 0) FROM pagamentos p
         WHERE p.caixa_id = c.id AND p.situacao = 'pago' AND p.forma_pagamento = 'dinheiro')
UNION ALL
SELECT '[deve ser 0] pagamentos recebidos depois do fechamento do caixa', COUNT(*)
  FROM pagamentos p JOIN caixas c ON c.id = p.caixa_id
 WHERE p.situacao = 'pago' AND c.fechado_em IS NOT NULL AND p.pago_em > c.fechado_em
-- Dados que impediriam CHECKs previstos para a migração 002:
UNION ALL
SELECT '[deve ser 0] preços com valor <= 0', COUNT(*) FROM precos WHERE valor <= 0
UNION ALL
SELECT '[deve ser 0] contratos com valor mensal <= 0', COUNT(*)
  FROM contratos_mensalistas WHERE valor_mensal <= 0
UNION ALL
SELECT '[deve ser 0] movimentações com valor cobrado negativo', COUNT(*)
  FROM movimentacoes WHERE valor_cobrado < 0
UNION ALL
SELECT '[deve ser 0] caixas com troco inicial negativo', COUNT(*)
  FROM caixas WHERE valor_inicial < 0
-- Volume atual:
UNION ALL SELECT '[informativo] clientes', COUNT(*) FROM clientes
UNION ALL SELECT '[informativo] veículos', COUNT(*) FROM veiculos
UNION ALL SELECT '[informativo] contratos (todos)', COUNT(*) FROM contratos_mensalistas
UNION ALL SELECT '[informativo] movimentações', COUNT(*) FROM movimentacoes
UNION ALL SELECT '[informativo] movimentações retroativas', COUNT(*) FROM movimentacoes WHERE retroativa = 1
UNION ALL SELECT '[informativo] movimentações canceladas', COUNT(*) FROM movimentacoes WHERE cancelada = 1
UNION ALL SELECT '[informativo] pagamentos', COUNT(*) FROM pagamentos
UNION ALL SELECT '[informativo] pagamentos cancelados', COUNT(*) FROM pagamentos WHERE situacao = 'cancelado'
UNION ALL SELECT '[informativo] caixas', COUNT(*) FROM caixas
UNION ALL SELECT '[informativo] registros de auditoria', COUNT(*) FROM auditoria;
