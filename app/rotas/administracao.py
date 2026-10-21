from flask import Blueprint, request, jsonify
from ..permissoes import exigir
from ..seguranca import exigir_login
from ..servicos.usuarios import criar_usuario
from ..db import conexao
from ..erros import ErroNegocio
bp=Blueprint("administracao",__name__)
@bp.get("/api/usuarios")
@exigir("usuarios")
def listar_usuarios():
    cur=conexao().cursor(dictionary=True); cur.execute("SELECT id,nome,email,login,nivel_acesso,trocar_senha,ativo,criado_em FROM usuarios ORDER BY nome"); r=cur.fetchall(); cur.close(); return jsonify(r)
@bp.post("/api/usuarios")
@exigir("usuarios")
def novo_usuario():
    d=request.get_json(force=True)
    uid=criar_usuario(d.get("nome"),d.get("email"),d.get("login"),d.get("senha_provisoria"),d.get("nivel_acesso"),exigir_login(),True)
    return jsonify({"id":uid,"mensagem":"Usuário criado. Ele deverá trocar a senha no próximo login."}),201
@bp.post("/api/usuarios/<int:uid>/desativar")
@exigir("usuarios")
def desativar(uid):
    atual=exigir_login()
    if uid==atual: raise ErroNegocio("Você não pode desativar o próprio usuário.")
    conn=conexao(); cur=conn.cursor(dictionary=True); cur.execute("SELECT nivel_acesso,ativo FROM usuarios WHERE id=%s",(uid,)); alvo=cur.fetchone(); cur.close()
    if not alvo: raise ErroNegocio("Usuário não encontrado.",404)
    if alvo["nivel_acesso"]=="administrador" and alvo["ativo"]:
        cur=conn.cursor(); cur.execute("SELECT COUNT(*) FROM usuarios WHERE nivel_acesso='administrador' AND ativo=1"); total=cur.fetchone()[0]; cur.close()
        if total<=1: raise ErroNegocio("É necessário manter pelo menos um administrador ativo.")
    cur=conn.cursor(); cur.execute("UPDATE usuarios SET ativo=0,atualizado_por=%s WHERE id=%s",(atual,uid)); conn.commit(); cur.close(); return jsonify({"mensagem":"Usuário desativado."})
@bp.get("/api/auditoria")
@exigir("auditoria")
def auditoria():
    cur=conexao().cursor(dictionary=True); cur.execute("SELECT a.id,a.tabela,a.registro_id,a.acao,a.usuario_id,u.nome AS usuario_nome,a.data_hora,a.dados_antes,a.dados_depois FROM auditoria a JOIN usuarios u ON u.id=a.usuario_id ORDER BY a.data_hora DESC LIMIT 500"); rows=cur.fetchall(); cur.close()
    for r in rows:
        for k in ("dados_antes","dados_depois"):
            if r[k] is not None and isinstance(r[k],(bytes,bytearray)): r[k]=r[k].decode("utf-8")
    return jsonify(rows)
