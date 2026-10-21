from flask import Blueprint, jsonify, request, session
from flask_wtf.csrf import generate_csrf
from ..permissoes import exigir
from ..seguranca import exigir_login
from ..servicos import sistema
from ..db import conexao, transacao
from ..erros import ErroNegocio
bp=Blueprint("sistema",__name__)
@bp.get("/api/csrf")
def csrf(): return jsonify({"csrf_token":generate_csrf()})
@bp.get("/api/status")
@exigir("operacao")
def status(): return jsonify(sistema.status_sistema())
@bp.get("/api/configuracoes")
@exigir("configuracoes")
def configuracoes(): return jsonify(sistema.status_sistema()["configuracoes"] or {})
@bp.put("/api/configuracoes")
@exigir("configuracoes")
def atualizar_configuracoes():
    d=request.get_json(force=True)
    try:
        tolerancia=int(d.get("tolerancia_minutos")); fracao=int(d.get("fracao_minutos")); nome=str(d.get("nome_estacionamento","")).strip(); regra=d.get("arredondamento")
        if tolerancia<0 or not 1<=fracao<=60 or regra not in ("hora_cheia","fracao") or not 1<=len(nome)<=80: raise ValueError
    except (ValueError,TypeError): raise ErroNegocio("Configurações inválidas.")
    conn=conexao()
    with transacao():
        cur=conn.cursor(); cur.execute("UPDATE configuracoes SET tolerancia_minutos=%s,fracao_minutos=%s,arredondamento=%s,nome_estacionamento=%s,atualizado_por=%s WHERE id=1",(tolerancia,fracao,regra,nome,exigir_login())); cur.close()
    return jsonify({"mensagem":"Configurações atualizadas."})
