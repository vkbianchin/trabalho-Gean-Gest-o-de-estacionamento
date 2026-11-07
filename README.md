# ParkFlow — Gestão de Estacionamento

Sistema web para operar um estacionamento: entrada e saída de veículos, cobrança por tempo, mensalistas com contrato, caixa por turno, financeiro, relatórios e auditoria. Projeto de estudo e portfólio feito com **Flask + MariaDB/MySQL**, com foco em regras de negócio corretas, segurança e código testado.

> Sem capturas de tela ainda: ao subir o sistema, tire prints de **Movimentações**, **Financeiro** e **Relatórios** e guarde em `docs/img/` para mostrar aqui.

## O que o sistema faz

| Área | Recursos |
|---|---|
| **Operação** | Entrada e saída por placa; mapa de vagas com tipo **carro/moto**; prévia da saída com **tempo total estacionado** e valor antes de confirmar; aviso de mensalista com mensalidade em atraso |
| **Cobrança** | Tolerância, cobrança por fração ou hora cheia e diária máxima — tudo configurável e calculado com `Decimal` |
| **Clientes** | Pessoa **física (CPF)** ou **jurídica (CNPJ)** com validação dos dígitos; endereço preenchido pelo CEP; veículos e **histórico por placa** |
| **Mensalistas** | Contratos, geração de mensalidades, recebimento e controle de atraso com carência configurável |
| **Caixa** | Abertura com troco, fechamento com dinheiro contado e diferença |
| **Financeiro** | Recebido por período, forma de pagamento e origem, receita por dia, ticket médio, inadimplência e fechamentos de caixa |
| **Relatórios** | Movimentações, recebimentos e horários de pico, com **exportação CSV** para Excel |
| **Recibo** | Recibo imprimível (PDF pelo navegador) com dados do estabelecimento e CPF/CNPJ — *sem valor fiscal* |
| **Manutenção** | Editar clientes, veículos e vagas; ativar/desativar com travas (não desativa vaga ocupada, cliente ou veículo com contrato vigente); redefinir senha e reativar usuários |
| **Cancelamentos** | Cancelar entrada lançada por engano e estornar pagamentos, sempre com motivo e auditoria (administrador) |
| **Segurança** | Login com bloqueio por tentativas, verificação em duas etapas (TOTP), CSRF, perfis administrador/operador, sessão revalidada no banco, cabeçalhos de segurança, auditoria de alterações; preferências de aparência salvas por usuário |

## Tecnologias

Python 3.12 · Flask 3 · Flask-WTF (CSRF) · mysql-connector-python (pool de conexões) · bcrypt · MariaDB 10.11 · HTML/CSS/JavaScript puro (sem framework, um arquivo por tela) · pytest · GitHub Actions

## Como rodar

```bash
git clone <seu-repositorio> && cd <pasta>
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # Windows: copy .env.example .env  — e preencha os valores
python -c "import secrets; print(secrets.token_hex(32))"   # use o resultado em FLASK_SECRET_KEY
```

**Banco de dados** (MariaDB 10.11):

1. Crie o banco e um usuário com poucas permissões (modelo em `scripts/permissoes_mysql.sql`).
2. Instalação nova: execute `banco/schema.sql`. Banco existente: aplique as migrações de `banco/migracoes/` em ordem (veja `banco/README.md`).
3. Crie o administrador e os dados iniciais:

```bash
python -m scripts.criar_primeiro_usuario
python -m scripts.dados_iniciais
python -m scripts.dados_teste        # opcional: clientes, vagas e movimentos fictícios para demonstração
python run.py                        # http://127.0.0.1:5000
```

**Testes:** `python -m pytest` roda os testes unitários (sem banco). Os testes de integração com MariaDB real ficam em `tests/integracao/` e rodam no GitHub Actions (job `banco-real`); para rodá-los na sua máquina, veja o cabeçalho de `tests/integracao/test_banco_real.py` (ele **apaga e recria** o banco de teste).

## Regra de cobrança

1. Até a **tolerância** (padrão 10 min) não se cobra nada.
2. Passada a tolerância, ela é descontada **uma vez** e o restante é arredondado **para cima** por fração (padrão 30 min) ou hora cheia.
3. Com **diária** cadastrada, cada bloco de 24 h cobra a diária e o resto nunca passa do valor dela.
4. Mensalistas não pagam na saída; o valor vem das mensalidades do contrato.

Exemplo: 2h35 de permanência, tolerância 10 min, fração 30 min, R$ 12/hora → 145 min a cobrar → 5 frações × R$ 6 = **R$ 30,00**.

## Estrutura

```
app/            código do sistema: rotas (HTTP) → servicos (regras) → db (MySQL)
  rotas/        uma blueprint por assunto (acesso, cadastros, financeiro, relatorios...)
  servicos/     regras de negócio e consultas
static/js/      nucleo.js (base, API, validações) + telas/<tela>.js (um arquivo por tela)
templates/      páginas HTML
banco/          schema.sql e migracoes/ (SQL versionado)
scripts/        criação do primeiro usuário, dados iniciais/teste, exportação do schema
tests/          testes automatizados
deploy/         exemplos de systemd, nginx e backup para uma VPS
docs/           arquitetura, API e histórico
```

Mais detalhes: [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md) · [`docs/API.md`](docs/API.md) · [`banco/README.md`](banco/README.md) · [`deploy/DEPLOY.md`](deploy/DEPLOY.md) · [`CHANGELOG.md`](CHANGELOG.md)

## Segurança

Segredos ficam no `.env` (fora do Git; use o `.env.example` como modelo). Senhas com bcrypt, CSRF em toda escrita, política de conteúdo (CSP) restrita, páginas sem cache (o botão "voltar" não reabre telas internas depois do logout), contas bloqueadas por 15 min após 5 erros e sessão conferida no banco a cada requisição (usuário desativado perde o acesso na hora).

## Limitações conhecidas e próximos passos

- O **estorno** não altera um caixa já fechado (decisão de projeto: um fechamento conferido não muda); esse ajuste fica para o responsável financeiro.
- A chave do **2FA** é guardada em texto no banco (como em muitos sistemas simples): proteja o acesso ao banco e aos backups. Não há QR Code nem códigos de recuperação; se o administrador perder o autenticador, outro administrador precisa desativar o 2FA direto no banco.
- O recibo **não é nota fiscal**; emitir NFS-e/NFC-e exigiria integração com a prefeitura/SEFAZ.
- O `schema.sql` foi **reconstruído a partir do código** e só foi validado pelo job `banco-real` da CI quando você o executar no GitHub; gere o oficial com `python -m scripts.exportar_schema` e compare.
- O código mais antigo do front-end (`nucleo.js` e algumas telas) ainda tem linhas muito longas; `ruff.toml` traz a configuração para rodar `ruff format` no Python e um formatador (Prettier) no JavaScript.
- Possíveis evoluções: multiunidade, perfis de supervisor/financeiro, códigos de recuperação do 2FA, modo offline.
