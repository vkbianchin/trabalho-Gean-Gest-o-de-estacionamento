from flask import Blueprint, request, jsonify, session, redirect, url_for
from ..servicos.usuarios import login, trocar_senha
from ..seguranca import exigir_login
from ..erros import ErroNegocio

bp=Blueprint("acesso",__name__)

@bp.post("/api/login")
def api_login():
    d=request.get_json(silent=True) or request.form
    usuario=login(d.get("login"),d.get("senha"))
    return jsonify({"usuario":usuario,"proxima":"/trocar-senha" if usuario["trocar_senha"] else "/"})

@bp.post("/api/logout")
def api_logout():
    session.clear(); return jsonify({"mensagem":"Sessão encerrada."})

@bp.get("/api/sessao")
def sessao_atual():
    if not session.get("usuario_id"): raise ErroNegocio("Faça login para continuar.",401)
    return jsonify({"usuario_id":session["usuario_id"],"nome":session["nome"],"login":session["login"],"nivel_acesso":session["nivel_acesso"],"trocar_senha":session["trocar_senha"],"preferencias":session.get("preferencias",{"tema":"escuro","tamanho_texto":"normal","cor_destaque":"azul","sons":"ligados"})})

@bp.put("/api/sessao/preferencias")
def atualizar_preferencias():
    if not session.get("usuario_id"):
        raise ErroNegocio("Faça login para continuar.",401)
    d=request.get_json(silent=True) or {}
    tema=d.get("tema","escuro")
    tamanho=d.get("tamanho_texto","normal")
    cor=d.get("cor_destaque","azul")
    sons=d.get("sons","ligados")
    if tema not in ("escuro","claro") or tamanho not in ("normal","grande") or cor not in ("azul","verde","violeta","dourado") or sons not in ("ligados","desligados"):
        raise ErroNegocio("Preferências inválidas.")
    preferencias={"tema":tema,"tamanho_texto":tamanho,"cor_destaque":cor,"sons":sons}
    session["preferencias"]=preferencias
    return jsonify({"mensagem":"Preferências salvas.","preferencias":preferencias})

@bp.post("/api/trocar-senha")
def api_trocar_senha():
    uid=session.get("usuario_id")
    if not uid: raise ErroNegocio("Faça login para continuar.",401)
    d=request.get_json(silent=True) or request.form
    trocar_senha(uid,d.get("senha_atual"),d.get("nova_senha")); return jsonify({"mensagem":"Senha alterada com sucesso.","proxima":"/"})

@bp.post("/api/sessao/renovar")
def renovar():
    exigir_login(); session.modified=True; return jsonify({"mensagem":"Sessão renovada."})
