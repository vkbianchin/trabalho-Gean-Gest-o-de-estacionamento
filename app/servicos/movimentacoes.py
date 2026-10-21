from datetime import datetime
from decimal import Decimal
from ..db import conexao, transacao
from ..erros import ErroNegocio
from ..validadores import placa
from ..cobranca import calcular_cobranca
from ..tempo import agora

def consultar_placa(valor):
    try: p = placa(valor)
    except ValueError as exc: raise ErroNegocio(str(exc))
    cur = conexao().cursor(dictionary=True)
    cur.execute("SELECT m.*,v.numero AS vaga_numero,p.nome AS plano_nome,t.nome AS tipo_nome FROM movimentacoes m JOIN vagas v ON v.id=m.vaga_id JOIN planos p ON p.id=m.plano_id JOIN tipos_veiculo t ON t.id=m.tipo_veiculo_id WHERE m.placa=%s AND m.aberta=1", (p,))
    aberta = cur.fetchone()
    cur.execute("SELECT v.id AS veiculo_id,v.tipo_veiculo_id,c.id AS cliente_id,c.nome AS cliente_nome,cm.id AS contrato_id,cm.valor_mensal,cm.data_inicio,cm.dia_vencimento FROM veiculos v JOIN clientes c ON c.id=v.cliente_id JOIN contratos_mensalistas cm ON cm.veiculo_id=v.id AND cm.data_fim IS NULL WHERE v.placa=%s AND v.ativo=1 AND c.ativo=1", (p,))
    mensalista = cur.fetchone()
    cur.close()
    return {"placa":p,"movimentacao_aberta":aberta,"mensalista":mensalista}

def registrar_entrada(valor_placa, tipo_veiculo_id, uid, vaga_id=None, retroativa=False, entrada_em=None):
    try: p=placa(valor_placa)
    except ValueError as exc: raise ErroNegocio(str(exc))
    if retroativa and not entrada_em: raise ErroNegocio("Informe a data e hora da entrada retroativa.")
    entrada_em = entrada_em or agora()
    cur = conexao().cursor(dictionary=True)
    cur.execute("SELECT id, tipo_veiculo_id, plano_id, numero FROM vagas WHERE ativo=1 AND tipo_veiculo_id=%s AND (%s IS NULL OR id=%s) ORDER BY numero", (tipo_veiculo_id,vaga_id,vaga_id))
    vagas=cur.fetchall()
    cur.execute("SELECT id FROM movimentacoes WHERE placa=%s AND aberta=1", (p,))
    ja_aberta=cur.fetchone()
    cur.execute("SELECT v.id AS veiculo_id,v.tipo_veiculo_id,cm.id AS contrato_id FROM veiculos v JOIN contratos_mensalistas cm ON cm.veiculo_id=v.id AND cm.data_fim IS NULL WHERE v.placa=%s AND v.ativo=1", (p,))
    mensalista=cur.fetchone()
    cur.close()
    if ja_aberta: raise ErroNegocio("Este veículo já está estacionado.")
    if mensalista and mensalista["tipo_veiculo_id"] != int(tipo_veiculo_id): raise ErroNegocio("O tipo de veículo não corresponde ao cadastro do mensalista.")
    # Mensalista só pode ocupar vaga do plano mensal; horista só vaga do plano por hora.
    conn=conexao()
    cur=conn.cursor(dictionary=True)
    cur.execute("SELECT id FROM planos WHERE cobranca=%s", ("mensal" if mensalista else "hora",))
    plano=cur.fetchone()
    if not plano: cur.close(); raise ErroNegocio("Plano necessário não encontrado. Execute os dados iniciais.")
    vagas=[v for v in vagas if v["plano_id"]==plano["id"]]
    escolhida=next((v for v in vagas if v["id"]==vaga_id), None) if vaga_id else (vagas[0] if vagas else None)
    if not escolhida: cur.close(); raise ErroNegocio("Não há vaga livre disponível para esse veículo e plano.")
    cur.execute("SELECT id FROM movimentacoes WHERE vaga_id=%s AND aberta=1", (escolhida["id"],))
    if cur.fetchone(): cur.close(); raise ErroNegocio("A vaga selecionada já está ocupada.")
    cur.close()
    with transacao():
        cur=conn.cursor()
        cur.execute("INSERT INTO movimentacoes (vaga_id,plano_id,tipo_veiculo_id,placa,veiculo_id,contrato_id,entrada_em,retroativa,criado_por) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", (escolhida["id"],plano["id"],tipo_veiculo_id,p,mensalista["veiculo_id"] if mensalista else None,mensalista["contrato_id"] if mensalista else None,entrada_em,int(retroativa),uid))
        mid=cur.lastrowid; cur.close()
    return {"id":mid,"placa":p,"vaga":escolhida["numero"],"mensalista":bool(mensalista)}

def registrar_saida(valor_placa, uid, caixa_id=None, forma_pagamento=None, retroativa=False, saida_em=None):
    try: p=placa(valor_placa)
    except ValueError as exc: raise ErroNegocio(str(exc))
    if retroativa and not saida_em: raise ErroNegocio("Informe a data e hora da saída retroativa.")
    saida_em=saida_em or agora()
    conn=conexao()
    cur=conn.cursor(dictionary=True)
    cur.execute("SELECT m.*,pl.cobranca,pr.valor AS valor_hora,pr.valor_diaria,c.tolerancia_minutos,c.arredondamento,c.fracao_minutos FROM movimentacoes m JOIN planos pl ON pl.id=m.plano_id JOIN precos pr ON pr.plano_id=m.plano_id AND pr.tipo_veiculo_id=m.tipo_veiculo_id JOIN configuracoes c ON c.id=1 WHERE m.placa=%s AND m.aberta=1", (p,))
    m=cur.fetchone(); cur.close()
    if not m: raise ErroNegocio("Não existe entrada aberta para esta placa.",404)
    if saida_em < m["entrada_em"]: raise ErroNegocio("A saída não pode ser anterior à entrada.")
    if m["cobranca"]=="mensal": valor=Decimal("0.00")
    else:
        valor=calcular_cobranca(m["entrada_em"],saida_em,m["valor_hora"],m["tolerancia_minutos"],m["arredondamento"],m["fracao_minutos"],m["valor_diaria"])
        if valor > 0:
            if not caixa_id or not forma_pagamento: raise ErroNegocio("Informe o caixa aberto e a forma de pagamento.")
            cur=conn.cursor(dictionary=True); cur.execute("SELECT id FROM caixas WHERE id=%s AND usuario_id=%s AND fechado_em IS NULL", (caixa_id,uid)); caixa=cur.fetchone(); cur.close()
            if not caixa: raise ErroNegocio("Abra seu caixa antes de receber pagamentos.")
    with transacao():
        cur=conn.cursor()
        cur.execute("UPDATE movimentacoes SET saida_em=%s,valor_cobrado=%s,retroativa=%s,atualizado_por=%s WHERE id=%s AND aberta=1", (saida_em,valor,int(retroativa),uid,m["id"]))
        if cur.rowcount != 1: cur.close(); raise ErroNegocio("A movimentação já foi encerrada. Atualize a consulta.",409)
        if m["cobranca"]=="hora" and valor>0:
            cur.execute("INSERT INTO pagamentos (movimentacao_id,valor,situacao,forma_pagamento,pago_em,caixa_id,criado_por) VALUES (%s,%s,'pago',%s,%s,%s,%s)", (m["id"],valor,forma_pagamento,saida_em,caixa_id,uid))
        cur.close()
    return {"id":m["id"],"placa":p,"valor":str(valor),"mensalista":m["cobranca"]=="mensal"}
