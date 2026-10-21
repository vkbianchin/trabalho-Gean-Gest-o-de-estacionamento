from app import create_app
from app.db import conexao

app=create_app()
with app.app_context():
    conn=conexao()
    cur=conn.cursor()
    cur.execute("SELECT VERSION(), DATABASE()")
    versao,banco=cur.fetchone()
    cur.close()
    print(f"Conexão OK. MySQL: {versao} | Banco: {banco}")
