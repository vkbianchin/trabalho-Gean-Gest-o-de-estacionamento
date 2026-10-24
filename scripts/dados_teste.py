"""Cadastra dados de TESTE usando as próprias regras do sistema (validações incluídas).

Uso (na pasta do projeto, com o ambiente virtual ativado):
    python -m scripts.dados_teste

- Mostra em qual banco vai gravar e só continua se você digitar SIM.
- Pode ser rodado várias vezes: o que já existe (CPF, placa, número de vaga, preço, contrato) é pulado.
- Os clientes de teste têm "(Teste)" no nome, para você encontrar e apagar depois.
"""
from collections import Counter
from datetime import date, timedelta

from app import create_app
from app.db import conexao
from app.erros import ErroNegocio
from app.servicos import cadastros, contratos, movimentacoes

CLIENTES = ["Ana Souza", "Bruno Lima", "Carla Mendes", "Diego Rocha", "Elisa Prado",
            "Fabio Teixeira", "Gabriela Nunes", "Henrique Alves", "Isabela Duarte", "Joao Ferreira"]
MARCAS_MODELOS = {"Fiat": ["Uno", "Argo"], "Volkswagen": ["Gol", "Polo"], "Chevrolet": ["Onix", "S10"],
                  "Honda": ["Civic", "CG 160"], "Toyota": ["Corolla"], "Yamaha": ["Fazer 250"]}
CARROS = [("Fiat", "Uno"), ("Volkswagen", "Gol"), ("Chevrolet", "Onix"), ("Honda", "Civic"),
          ("Toyota", "Corolla"), ("Fiat", "Argo"), ("Volkswagen", "Polo"), ("Chevrolet", "S10")]
MOTOS = [("Honda", "CG 160"), ("Yamaha", "Fazer 250")]

resumo = Counter()


def gerar_cpf(base):
    d = [int(c) for c in f"{base:09d}"]
    for n in (9, 10):
        soma = sum(d[i] * (n + 1 - i) for i in range(n))
        d.append((soma * 10 % 11) % 10)
    return "".join(map(str, d))


def tentar(rotulo, fn):
    """Roda uma criação; conta criado/pulado/erro sem interromper o script."""
    try:
        r = fn()
        resumo[f"{rotulo}: criado"] += 1
        return r
    except ErroNegocio as exc:
        if exc.status == 409:
            resumo[f"{rotulo}: já existia"] += 1
        else:
            resumo[f"{rotulo}: erro"] += 1
            print(f"  ! {rotulo}: {exc.mensagem}")
    except Exception as exc:  # erro inesperado: mostra e segue
        resumo[f"{rotulo}: erro"] += 1
        print(f"  ! {rotulo}: {exc}")
    try:
        conexao().rollback()
    except Exception:
        pass
    return None


def um(sql, params=()):
    cur = conexao().cursor(dictionary=True)
    cur.execute(sql, params)
    r = cur.fetchone()
    cur.close()
    return r


def id_por_nome(tabela, nome):
    r = um(f"SELECT id FROM {tabela} WHERE LOWER(nome)=LOWER(%s) ORDER BY id LIMIT 1", (nome,))
    return r["id"] if r else None


def main():
    app = create_app()
    with app.app_context():
        info = um("SELECT DATABASE() AS banco, @@hostname AS servidor")
        print(f"Banco: {info['banco']} (servidor {info['servidor']})")
        if input("Gravar dados de TESTE neste banco? Digite SIM para continuar: ").strip() != "SIM":
            raise SystemExit("Cancelado. Nada foi gravado.")
        adm = um("SELECT id FROM usuarios WHERE ativo=1 AND nivel_acesso='administrador' ORDER BY id LIMIT 1")
        if not adm:
            raise SystemExit("Crie o primeiro administrador antes de rodar este script.")
        uid = adm["id"]

        tipos = {t["nome"].lower(): t["id"] for t in cadastros.listar_catalogo("tipos_veiculo")}
        planos = {p["cobranca"]: p["id"] for p in cadastros.listar_catalogo("planos")}
        cores = [c["id"] for c in cadastros.listar_catalogo("cores")]
        if "carro" not in tipos or "moto" not in tipos or "mensal" not in planos or "hora" not in planos:
            raise SystemExit("Faltam tipos Carro/Moto ou planos Mensal/Hora. Rode: python -m scripts.dados_iniciais")
        carro, moto = tipos["carro"], tipos["moto"]

        print("Marcas e modelos...")
        modelos = {}
        for marca, lista in MARCAS_MODELOS.items():
            mid = id_por_nome("marcas", marca) or tentar("marca", lambda m=marca: cadastros.criar_item_catalogo("marcas", {"nome": m}, uid))
            mid = mid or id_por_nome("marcas", marca)
            for nome in lista:
                oid = id_por_nome("modelos", nome) or tentar("modelo", lambda n=nome, m=mid: cadastros.criar_item_catalogo("modelos", {"nome": n, "marca_id": m}, uid))
                modelos[(marca, nome)] = oid or id_por_nome("modelos", nome)

        print("Preços do plano horista...")
        for tid, valor, diaria in ((carro, "5.00", "40.00"), (moto, "3.00", "25.00")):
            tentar("preço", lambda t=tid, v=valor, d=diaria: cadastros.criar_preco(
                {"plano_id": planos["hora"], "tipo_veiculo_id": t, "valor": v, "valor_diaria": d}, uid))

        print("Vagas...")
        vagas = [(n, carro, "mensal") for n in range(1, 11)] + [(n, carro, "hora") for n in range(11, 21)] \
              + [(n, moto, "mensal") for n in (21, 22)] + [(n, moto, "hora") for n in (23, 24)]
        for numero, tid, cob in vagas:
            tentar("vaga", lambda n=numero, t=tid, c=cob: cadastros.criar_vaga(
                {"numero": n, "tipo_veiculo_id": t, "plano_id": planos[c]}, uid))

        print("Clientes...")
        clientes = []
        for i, nome in enumerate(CLIENTES):
            cpf = gerar_cpf(100200300 + i * 7919)
            ja = um("SELECT id FROM clientes WHERE cpf=%s", (cpf,))
            if ja:
                resumo["cliente: já existia"] += 1
                clientes.append(ja["id"])
                continue
            cid = tentar("cliente", lambda n=nome, c=cpf, k=i: cadastros.criar_cliente({
                "nome": f"{n} (Teste)", "cpf": c, "telefone": f"4999991{k:04d}", "email": f"teste{k + 1}@exemplo.com",
                "cep": "89560000", "logradouro": "Rua das Flores", "numero": str(10 + k), "bairro": "Centro",
                "cidade": "Videira", "uf": "SC"}, uid))
            clientes.append(cid)

        print("Veículos...")
        veiculos = []  # (placa, cliente_id, veiculo_id, tipo_id)
        for i in range(15):
            cid = clientes[i % len(clientes)]
            if not cid:
                continue
            eh_moto = i % 5 == 4
            marca, modelo = (MOTOS if eh_moto else CARROS)[i % len(MOTOS if eh_moto else CARROS)]
            placa = f"TST1{chr(65 + i % 6)}{i + 1:02d}"
            tid = moto if eh_moto else carro
            ja = um("SELECT id FROM veiculos WHERE placa=%s", (placa,))
            if ja:
                resumo["veículo: já existia"] += 1
                veiculos.append((placa, cid, ja["id"], tid))
                continue
            vid = tentar("veículo", lambda p=placa, c=cid, t=tid, mm=modelos.get((marca, modelo)), k=i: cadastros.criar_veiculo(
                {"placa": p, "cliente_id": c, "tipo_veiculo_id": t, "modelo_id": mm, "cor_id": cores[k % len(cores)] if cores else None}, uid))
            if vid:
                veiculos.append((placa, cid, vid, tid))

        print("Contratos mensalistas...")
        mensalistas = []
        for placa, cid, vid, tid in veiculos[:6]:
            if um("SELECT id FROM contratos_mensalistas WHERE veiculo_id=%s AND data_fim IS NULL", (vid,)):
                resumo["contrato: já existia"] += 1
                mensalistas.append((placa, tid))
                continue
            ok = tentar("contrato", lambda c=cid, v=vid, t=tid: contratos.criar({
                "cliente_id": c, "veiculo_id": v, "valor_mensal": "120.00" if t == moto else "250.00",
                "dia_vencimento": 10, "data_inicio": (date.today() - timedelta(days=30)).isoformat()}, uid))
            if ok:
                mensalistas.append((placa, tid))

        print("Entradas (veículos estacionados)...")
        horistas = [(p, t) for p, c, v, t in veiculos[6:] ][:3]
        for placa, tid in mensalistas[:3] + horistas:
            if um("SELECT id FROM movimentacoes WHERE placa=%s AND aberta=1", (placa,)):
                resumo["entrada: já existia"] += 1
                continue
            tentar("entrada", lambda p=placa, t=tid: movimentacoes.registrar_entrada(p, t, uid))

        print("\nResumo:")
        for chave in sorted(resumo):
            print(f"  {chave}: {resumo[chave]}")
        print("\nPronto. Abra o sistema e atualize as telas (Ctrl+F5).")


if __name__ == "__main__":
    main()
