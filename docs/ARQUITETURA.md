# Arquitetura

## Camadas

```
Navegador (HTML + CSS + JS)
   │  fetch JSON  ·  CSRF  ·  cookie de sessão
   ▼
app/rotas/*      recebem a requisição, checam permissão (@exigir) e devolvem JSON/HTML
   ▼
app/servicos/*   regras de negócio: validação, cobrança, caixa, mensalidades, relatórios
   ▼
app/db.py        pool de conexões e transações     →   MariaDB/MySQL
```

Regra do projeto: **rota recebe e responde, serviço decide, banco guarda.** Funções puras (cobrança, duração, validação de CPF/CNPJ, CSV, histórico) ficam separadas do acesso ao banco para serem testadas sem ele.

## Módulos principais

| Módulo | Responsabilidade |
|---|---|
| `app/__init__.py` | Fábrica do app: sessão, CSRF, cabeçalhos de segurança, JSON com datas ISO, log |
| `app/permissoes.py` | Tabela única de permissões por perfil (usada pelas APIs **e** pelas páginas) |
| `app/seguranca.py` | Hash de senha (bcrypt) e revalidação da sessão contra o banco |
| `app/cobranca.py` | Cálculo do valor a cobrar (`Decimal`, tolerância, fração, diária) |
| `app/validadores.py` | Placa, CPF, CNPJ, e-mail, CEP, telefone, texto (sem `@` fora do e-mail) |
| `app/auditoria.py` | Registro imutável de quem alterou o quê (valores antes/depois) |
| `app/servicos/movimentacoes.py` | Entrada, prévia e registro de saída, histórico por placa |
| `app/servicos/financeiro.py` · `relatorios.py` | Indicadores e relatórios do período |
| `app/servicos/recibos.py` | Dados do recibo |
| `app/servicos/manutencao.py` | Editar e ativar/desativar clientes, veículos e vagas, com travas |
| `app/servicos/cancelamentos.py` | Cancelar entradas e estornar pagamentos (motivo + auditoria) |
| `app/totp.py` | Códigos de uso único baseados em tempo (RFC 6238), só com a biblioteca padrão |
| `app/exportacao.py` | CSV para Excel com proteção contra injeção de fórmula |

## Decisões de projeto

- **O valor cobrado é gravado na saída** (`movimentacoes.valor_cobrado`). Mudar preços depois não altera o passado.
- **Auditoria só de inserção:** o script `scripts/permissoes_mysql.sql` revoga `UPDATE` e `DELETE` da tabela de auditoria para o usuário do sistema (confira se foi aplicado no seu banco).
- **Uma vaga e uma placa só podem ter uma movimentação aberta.** A aplicação confere antes de gravar e, para o caso de duas entradas simultâneas, trata o erro 1062 do banco como "outra entrada acabou de ocupar esta vaga ou placa"; o `schema.sql` traz os índices únicos que isso pressupõe (marcados `[CONFERIR]`).
- **Pagamento único para horista e mensalidade:** `pagamentos` liga a uma movimentação *ou* a um contrato.
- **Datas em horário de Brasília, sem fuso**, em todo o sistema; a API as devolve em ISO 8601 (`2026-10-30T10:00:00`).
- **Sessão revalidada no banco:** desativar um usuário ou mudar o perfil dele vale na próxima requisição.
- **Páginas e APIs com `Cache-Control: no-store`:** depois do logout, o botão "voltar" não mostra telas internas; a tela de login também redireciona quem já está logado.
- **Recibo, não nota fiscal:** documento simples em HTML imprimível; a emissão fiscal exigiria integração externa.
- **Front-end sem framework, um arquivo por tela:** `static/js/nucleo.js` guarda a base (API, CSRF, validações, janelas, menu) e expõe `window.ParkFlow`; cada tela vive em `static/js/telas/<tela>.js` e se registra em `ParkFlow.telas`. O `base.html` carrega só o arquivo da página aberta.
- **Cancelar não apaga:** uma entrada cancelada fica no histórico, marcada (`cancelada=1`), com a vaga liberada (`saida_em = entrada_em`); um estorno de mensalidade volta o pagamento para `aberto`. Em ambos, motivo e usuário vão para a auditoria. Estornar um caixa já fechado é bloqueado.
- **Colunas opcionais (migrações 005 e 006):** preferências salvas e 2FA são lidas por uma função que tolera a coluna ausente; sem a migração o sistema funciona, só sem esses recursos.

## Testes

`python -m pytest` roda sem banco: o acesso ao MySQL é substituído por dados falsos onde necessário. Cobrem cobrança, validadores, login e bloqueio, CSRF, permissões das páginas e APIs, cabeçalhos de segurança, revalidação de sessão, saída/histórico/atraso, configurações, cadastro de cliente PF/PJ, CSV e recibo. **Não cobrem** o SQL em si — isso exige testar com um banco real.
