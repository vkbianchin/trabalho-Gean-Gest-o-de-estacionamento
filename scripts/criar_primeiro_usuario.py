import getpass
from app import create_app
from app.db import conexao
from app.servicos.usuarios import criar_usuario

app=create_app()
with app.app_context():
    conn=conexao(); cur=conn.cursor(); cur.execute("SELECT COUNT(*) FROM usuarios"); total=cur.fetchone()[0]; cur.close()
    if total:
        print("Já existe pelo menos um usuário. Este script só cria o primeiro administrador.")
        raise SystemExit(1)
    nome=input("Nome do administrador: ").strip()
    email=input("E-mail: ").strip()
    login=input("Login: ").strip()
    senha=getpass.getpass("Senha (mínimo 8 caracteres, letras e números): ")
    confirmacao=getpass.getpass("Confirme a senha: ")
    if senha!=confirmacao: raise SystemExit("As senhas não conferem.")
    uid=criar_usuario(nome,email,login,senha,"administrador",None,False)
    print(f"Administrador criado com ID {uid}.")
