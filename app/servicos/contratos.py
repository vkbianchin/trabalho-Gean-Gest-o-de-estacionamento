from datetime import date
from ..db import conexao, transacao
from ..erros import ErroNegocio
from ..validadores import dinheiro

def criar(d, uid):
    try:
        cliente_id=int(d["cliente_id"]); veiculo_id=int(d["veiculo_id"]); valor=dinheiro(d["valor_mensal"],"valor mensal",False); dia=int(d["dia_vencimento"]); inicio=date.fromisoformat(d["data_inicio"])
        if not 1<=dia<=28: raise ValueError("Dia de vencimento deve estar entre 1 e 28.")
    except (KeyError,ValueError,TypeError) as exc: raise ErroNegocio(str(exc) or "Dados do contrato inválidos.")
    cur=conexao().cursor(dictionary=True); cur.execute("SELECT id FROM veiculos WHERE id=%s AND cliente_id=%s AND ativo=1",(veiculo_id,cliente_id)); v=cur.fetchone(); cur.close()
    if not v: raise ErroNegocio("O veículo não pertence ao cliente selecionado.")
    conn=conexao()
    with transacao():
        cur=conn.cursor(); cur.execute("INSERT INTO contratos_mensalistas (cliente_id,veiculo_id,valor_mensal,dia_vencimento,data_inicio,criado_por) VALUES (%s,%s,%s,%s,%s,%s)",(cliente_id,veiculo_id,valor,dia,inicio,uid)); cid=cur.lastrowid; cur.close()
    return cid

def encerrar(contrato_id, uid, data_fim, motivo):
    try: fim=date.fromisoformat(data_fim)
    except (ValueError,TypeError): raise ErroNegocio("Data de encerramento inválida.")
    if fim>date.today(): raise ErroNegocio("A data de encerramento não pode estar no futuro.")
    if motivo not in {"cancelado_cliente","inadimplencia","troca_veiculo","outro"}: raise ErroNegocio("Motivo de encerramento inválido.")
    conn=conexao(); cur=conn.cursor(dictionary=True); cur.execute("SELECT veiculo_id FROM contratos_mensalistas WHERE id=%s AND data_fim IS NULL",(contrato_id,)); c=cur.fetchone(); cur.close()
    if not c: raise ErroNegocio("Contrato vigente não encontrado.",404)
    cur=conn.cursor(); cur.execute("SELECT id FROM movimentacoes WHERE veiculo_id=%s AND aberta=1",(c["veiculo_id"],)); estacionado=cur.fetchone(); cur.close()
    if estacionado: raise ErroNegocio("Não é possível encerrar o contrato enquanto o veículo estiver estacionado.")
    with transacao():
        cur=conn.cursor(); cur.execute("UPDATE contratos_mensalistas SET data_fim=%s,motivo_encerramento=%s,atualizado_por=%s WHERE id=%s AND data_fim IS NULL",(fim,motivo,uid,contrato_id)); cur.close()
