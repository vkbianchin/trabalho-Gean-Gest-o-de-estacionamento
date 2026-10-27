from datetime import date
from mysql.connector.errors import IntegrityError
from ..db import conexao, transacao
from ..erros import ErroNegocio
from ..tempo import agora
from ..validadores import dinheiro

def vaga_mensal_disponivel(contratos_vigentes, vagas_mensais):
    """Um contrato novo só cabe se houver mais vagas mensais ativas do que contratos vigentes do mesmo tipo."""
    return contratos_vigentes < vagas_mensais

def criar(d, uid):
    try:
        cliente_id=int(d["cliente_id"]); veiculo_id=int(d["veiculo_id"]); valor=dinheiro(d["valor_mensal"],"valor mensal",False); dia=int(d["dia_vencimento"]); inicio=date.fromisoformat(d["data_inicio"])
        if not 1<=dia<=28: raise ValueError("Dia de vencimento deve estar entre 1 e 28.")
    except (KeyError,ValueError,TypeError) as exc: raise ErroNegocio(str(exc) or "Dados do contrato inválidos.")
    conn=conexao()
    cur=conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT v.tipo_veiculo_id, v.ativo AS veiculo_ativo, c.ativo AS cliente_ativo FROM veiculos v JOIN clientes c ON c.id=v.cliente_id WHERE v.id=%s AND v.cliente_id=%s",(veiculo_id,cliente_id))
        v=cur.fetchone()
        if not v: raise ErroNegocio("O veículo não pertence ao cliente selecionado.")
        if not v["cliente_ativo"]: raise ErroNegocio("O cliente está inativo.")
        if not v["veiculo_ativo"]: raise ErroNegocio("O veículo está inativo.")
        cur.execute("SELECT id FROM contratos_mensalistas WHERE veiculo_id=%s AND data_fim IS NULL",(veiculo_id,))
        if cur.fetchone(): raise ErroNegocio("Este veículo já possui um contrato vigente.")
        cur.execute("SELECT COUNT(*) AS n FROM contratos_mensalistas c JOIN veiculos v ON v.id=c.veiculo_id WHERE c.data_fim IS NULL AND v.tipo_veiculo_id=%s",(v["tipo_veiculo_id"],))
        vigentes=cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) AS n FROM vagas g JOIN planos p ON p.id=g.plano_id WHERE g.ativo=1 AND p.cobranca='mensal' AND g.tipo_veiculo_id=%s",(v["tipo_veiculo_id"],))
        vagas_mensais=cur.fetchone()["n"]
        if not vaga_mensal_disponivel(vigentes,vagas_mensais):
            raise ErroNegocio("Não há vaga mensal disponível para este tipo de veículo. Cadastre ou converta uma vaga para o plano mensal.")
    finally:
        cur.close()
    try:
        with transacao():
            cur=conn.cursor(); cur.execute("INSERT INTO contratos_mensalistas (cliente_id,veiculo_id,valor_mensal,dia_vencimento,data_inicio,criado_por) VALUES (%s,%s,%s,%s,%s,%s)",(cliente_id,veiculo_id,valor,dia,inicio,uid)); cid=cur.lastrowid; cur.close()
    except IntegrityError as exc:
        if getattr(exc,"errno",None)==1062: raise ErroNegocio("Este veículo já possui um contrato vigente.",409)
        raise
    return cid

def encerrar(contrato_id, uid, data_fim, motivo):
    try: fim=date.fromisoformat(data_fim)
    except (ValueError,TypeError): raise ErroNegocio("Data de encerramento inválida.")
    if fim>agora().date(): raise ErroNegocio("A data de encerramento não pode estar no futuro.")
    if motivo not in {"cancelado_cliente","inadimplencia","troca_veiculo","outro"}: raise ErroNegocio("Motivo de encerramento inválido.")
    conn=conexao(); cur=conn.cursor(dictionary=True); cur.execute("SELECT veiculo_id FROM contratos_mensalistas WHERE id=%s AND data_fim IS NULL",(contrato_id,)); c=cur.fetchone(); cur.close()
    if not c: raise ErroNegocio("Contrato vigente não encontrado.",404)
    cur=conn.cursor(); cur.execute("SELECT id FROM movimentacoes WHERE veiculo_id=%s AND aberta=1",(c["veiculo_id"],)); estacionado=cur.fetchone(); cur.close()
    if estacionado: raise ErroNegocio("Não é possível encerrar o contrato enquanto o veículo estiver estacionado.")
    with transacao():
        cur=conn.cursor(); cur.execute("UPDATE contratos_mensalistas SET data_fim=%s,motivo_encerramento=%s,atualizado_por=%s WHERE id=%s AND data_fim IS NULL",(fim,motivo,uid,contrato_id)); cur.close()
