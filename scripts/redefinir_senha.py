import getpass
from app import create_app
from app.db import conexao
from app.seguranca import gerar_hash

app=create_app()
with app.app_context():
    login=input("Login do usuário: ").strip()
    senha=getpass.getpass("Nova senha provisória: ")
    hash_senha=gerar_hash(senha)
    conn=conexao(); cur=conn.cursor()
    cur.execute("UPDATE usuarios SET senha_hash=%s,trocar_senha=1 WHERE login=%s AND ativo=1",(hash_senha,login))
    if cur.rowcount!=1:
        conn.rollback(); cur.close(); raise SystemExit("Usuário ativo não encontrado.")
    conn.commit(); cur.close()
    print("Senha redefinida. O usuário deverá trocá-la no próximo login.")
