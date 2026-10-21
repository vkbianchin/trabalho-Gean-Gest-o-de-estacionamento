from .db import conexao

class Repositorio:
    """Camada centralizada de SQL. Use parâmetros (%s), nunca concatene dados do usuário."""
    @staticmethod
    def um(sql, parametros=()):
        conn = conexao()
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, parametros)
        resultado = cur.fetchone()
        cur.close()
        return resultado

    @staticmethod
    def todos(sql, parametros=()):
        conn = conexao()
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, parametros)
        resultado = cur.fetchall()
        cur.close()
        return resultado

    @staticmethod
    def executar(sql, parametros=()):
        conn = conexao()
        cur = conn.cursor()
        cur.execute(sql, parametros)
        novo_id = cur.lastrowid
        cur.close()
        return novo_id
