from flask import Blueprint, request, jsonify
from ..permissoes import exigir
from ..seguranca import exigir_login
from ..servicos import caixa
bp=Blueprint("caixa",__name__)
@bp.get("/api/caixa")
@exigir("operacao")
def atual():
    c=caixa.caixa_aberto(exigir_login())
    if not c: return jsonify({"aberto":False})
    c["aberto"]=True
    for k in ("valor_inicial","dinheiro_esperado","dinheiro_contado","diferenca"):
        if c.get(k) is not None: c[k]=str(c[k])
    return jsonify(c)
@bp.post("/api/caixa/abrir")
@exigir("operacao")
def abrir(): return jsonify(caixa.abrir(exigir_login(),(request.get_json(force=True)).get("valor_inicial"))),201
@bp.post("/api/caixa/fechar")
@exigir("operacao")
def fechar():
    d=request.get_json(force=True); return jsonify(caixa.fechar(exigir_login(),d.get("dinheiro_contado"),d.get("observacao")))
