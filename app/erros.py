from flask import jsonify, request, render_template
from mysql.connector import Error as MySQLError

class ErroNegocio(Exception):
    def __init__(self, mensagem, status=400):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status

def registrar_erros(app):
    @app.errorhandler(ErroNegocio)
    def erro_negocio(exc):
        if request.path.startswith("/api/"):
            return jsonify({"erro": exc.mensagem}), exc.status
        return render_template("_em_construcao.html", mensagem=exc.mensagem), exc.status

    @app.errorhandler(404)
    def nao_encontrado(_exc):
        if request.path.startswith("/api/"):
            return jsonify({"erro": "Recurso não encontrado."}), 404
        return render_template("_em_construcao.html", mensagem="Página não encontrada."), 404

    @app.errorhandler(500)
    def erro_interno(exc):
        app.logger.exception("Erro interno: %s", exc)
        if request.path.startswith("/api/"):
            return jsonify({"erro": "Ocorreu um erro interno. Consulte o log do sistema."}), 500
        return render_template("_em_construcao.html", mensagem="Ocorreu um erro interno."), 500

    @app.errorhandler(MySQLError)
    def erro_mysql(exc):
        app.logger.exception("Erro MySQL: %s", exc)
        mensagem = "Não foi possível concluir a operação no banco de dados. Verifique os dados e tente novamente."
        if getattr(exc, "errno", None) == 1062:
            mensagem = "Já existe um registro com esses dados. Verifique placa, login, e-mail ou número da vaga."
        elif getattr(exc, "errno", None) == 1452:
            mensagem = "Um dos registros relacionados não existe ou não está disponível."
        if request.path.startswith("/api/"):
            return jsonify({"erro": mensagem}), 409 if getattr(exc, "errno", None) in (1062, 1452) else 500
        return render_template("_em_construcao.html", mensagem=mensagem), 500
