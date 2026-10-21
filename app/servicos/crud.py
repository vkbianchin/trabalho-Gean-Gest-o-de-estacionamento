from ..db import conexao

# Consultas de leitura explicitamente permitidas; escrita de cada domínio fica no serviço correspondente.
CONSULTAS = {
    "clientes": "SELECT id,nome,cpf,telefone,email,cidade,uf,ativo FROM clientes ORDER BY nome",
    "veiculos": "SELECT v.id,v.placa,v.cliente_id,c.nome AS cliente_nome,t.nome AS tipo_veiculo,m.nome AS modelo,co.nome AS cor,v.ativo FROM veiculos v JOIN clientes c ON c.id=v.cliente_id JOIN tipos_veiculo t ON t.id=v.tipo_veiculo_id LEFT JOIN modelos m ON m.id=v.modelo_id LEFT JOIN cores co ON co.id=v.cor_id ORDER BY v.placa",
    "vagas": "SELECT v.id,v.numero,v.tipo_veiculo_id,t.nome AS tipo_veiculo,v.plano_id,p.nome AS plano,v.ativo,CASE WHEN EXISTS (SELECT 1 FROM movimentacoes mv WHERE mv.vaga_id=v.id AND mv.aberta=1) THEN 1 ELSE 0 END AS ocupada FROM vagas v JOIN tipos_veiculo t ON t.id=v.tipo_veiculo_id JOIN planos p ON p.id=v.plano_id ORDER BY v.numero",
    "contratos": "SELECT cm.*,c.nome AS cliente_nome,v.placa FROM contratos_mensalistas cm JOIN clientes c ON c.id=cm.cliente_id JOIN veiculos v ON v.id=cm.veiculo_id ORDER BY cm.data_inicio DESC",
    "pagamentos": "SELECT p.*,c.nome AS cliente_nome,v.placa FROM pagamentos p LEFT JOIN contratos_mensalistas cm ON cm.id=p.contrato_id LEFT JOIN clientes c ON c.id=cm.cliente_id LEFT JOIN movimentacoes m ON m.id=p.movimentacao_id LEFT JOIN veiculos v ON v.id=cm.veiculo_id ORDER BY p.criado_em DESC LIMIT 500",
    "movimentacoes": "SELECT m.*,v.numero AS vaga_numero FROM movimentacoes m JOIN vagas v ON v.id=m.vaga_id ORDER BY m.entrada_em DESC LIMIT 200",
}

def listar(nome):
    if nome not in CONSULTAS: raise ValueError("Consulta não permitida.")
    cur=conexao().cursor(dictionary=True); cur.execute(CONSULTAS[nome]); rows=cur.fetchall(); cur.close(); return rows
