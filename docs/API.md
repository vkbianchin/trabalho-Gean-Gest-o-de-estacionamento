# API do ParkFlow

Todas as rotas `/api/*` respondem JSON (exceto os `.csv`). Erros têm o formato `{"erro": "mensagem"}` com o status HTTP adequado (400 dados inválidos, 401 sem login, 403 sem permissão, 404 não encontrado, 409 conflito).

Requisições que alteram dados (`POST`, `PUT`) exigem o cabeçalho `X-CSRFToken` com o valor de `GET /api/csrf`. Datas e horas saem em ISO 8601 sem fuso (`2026-10-30T10:00:00`, horário de Brasília). Valores monetários saem como texto com duas casas (`"12.50"`).

Este arquivo foi gerado a partir das rotas do código; as permissões vêm de `app/permissoes.py`.


## Acesso

| Método | Rota | O que faz |
|---|---|---|
| POST | `/api/login` | Entrar (login ou e-mail + senha). Bloqueia a conta após 5 falhas seguidas. |
| POST | `/api/logout` | Encerrar a sessão. |
| GET | `/api/sessao` | Dados do usuário logado e preferências de aparência. |
| PUT | `/api/sessao/preferencias` | Salvar tema, tamanho do texto, cor e sons (valem durante a sessão). |
| POST | `/api/trocar-senha` | Trocar a própria senha (obrigatório no primeiro acesso). |
| POST | `/api/sessao/renovar` | Renovar o tempo da sessão. |
| GET | `/api/csrf` | Token CSRF (enviado no cabeçalho X-CSRFToken nas requisições que alteram dados). |
| GET | `/saude` | Verificação de funcionamento para monitoramento (200 = ok, 503 = banco indisponível). |
| POST | `/api/login/2fa` | Segunda etapa do login: código de 6 dígitos do aplicativo autenticador. |
| GET | `/api/2fa` | Situação da verificação em duas etapas da conta. |
| POST | `/api/2fa/iniciar` | Gera a chave do autenticador (só vale depois de confirmada). |
| POST | `/api/2fa/confirmar` | Confirma com um código e ativa. |
| POST | `/api/2fa/desativar` | Desativa (exige senha e código). |

## Operação (administrador e operador)

| Método | Rota | O que faz |
|---|---|---|
| GET | `/api/placa/<valor_placa>` | Situação da placa: no local? mensalista? mensalidade em atraso? |
| GET | `/api/movimentacoes` | Últimas 200 movimentações. |
| POST | `/api/entrada` | Registrar entrada. |
| GET | `/api/saida/previa/<valor_placa>` | Prévia da saída: permanência e valor agora, sem gravar nada. |
| POST | `/api/saida` | Registrar saída; devolve tempo total, valor e (se houve cobrança) o id do pagamento. |
| GET | `/api/historico/<valor_placa>` | Todas as passagens da placa, com totais. |
| GET | `/api/caixa` | Caixa aberto do usuário (ou situação fechado). |
| POST | `/api/caixa/abrir` | Abrir caixa com troco inicial. |
| POST | `/api/caixa/fechar` | Fechar caixa informando o dinheiro contado. |
| GET | `/api/pagamentos` | Últimos 500 pagamentos. |
| POST | `/api/pagamentos/<int:pagamento_id>/receber` | Receber mensalidade. |
| GET | `/recibo/pagamento/<int:pagamento_id>` | Recibo imprimível de um pagamento recebido. Parâmetro opcional: documento (CPF/CNPJ). |
| GET | `/api/status` | Configurações e número de vagas ativas. |

## Cadastros (administrador e operador)

| Método | Rota | O que faz |
|---|---|---|
| GET | `/api/clientes` | Listar clientes (pessoa física ou jurídica). |
| POST | `/api/clientes` | Cadastrar cliente com CPF ou CNPJ. |
| GET | `/api/veiculos` | Listar veículos. |
| POST | `/api/veiculos` | Cadastrar veículo. |
| GET | `/api/vagas` | Listar vagas (com tipo, plano e se estão ocupadas). |
| POST | `/api/vagas` | Criar vaga. |
| GET | `/api/catalogos/<nome>` | Listar catálogo (marcas, tipos_veiculo, modelos, cores, planos). |
| POST | `/api/catalogos/<nome>` | Criar item de catálogo (marcas, modelos, cores). |
| GET | `/api/precos` | Listar preços por plano e tipo de veículo. |
| GET | `/api/clientes/<int:cid>` | Dados completos de um cliente. |
| PUT | `/api/clientes/<int:cid>` | Editar contato e endereço (CPF/CNPJ e tipo não mudam). |
| GET | `/api/veiculos/<int:vid>` | Dados de um veículo (com ids de modelo e cor). |
| PUT | `/api/veiculos/<int:vid>` | Editar modelo e cor (placa, dono e tipo não mudam). |

## Somente administrador

| Método | Rota | O que faz |
|---|---|---|
| POST | `/api/catalogos/tipos_veiculo` | Criar tipo de veículo. |
| POST | `/api/planos` | Criar plano. |
| PUT | `/api/planos/<int:plano_id>` | Renomear plano. |
| POST | `/api/planos/<int:plano_id>/ativo` | Ativar/desativar plano. |
| POST | `/api/precos` | Criar preço. |
| PUT | `/api/precos/<int:preco_id>` | Alterar preço. |
| GET | `/api/contratos` | Listar contratos de mensalistas. |
| POST | `/api/contratos` | Criar contrato. |
| POST | `/api/contratos/<int:contrato_id>/encerrar` | Encerrar contrato com motivo. |
| POST | `/api/pagamentos/gerar-mensalidades` | Gerar as mensalidades do mês para os contratos vigentes. |
| GET | `/api/financeiro/resumo` | Totais do período: recebido, por forma, por origem, por dia, ticket médio, atrasos. Parâmetros: inicio, fim (AAAA-MM-DD). |
| GET | `/api/financeiro/inadimplencia` | Mensalidades vencidas e não pagas (considera a carência configurada). |
| GET | `/api/financeiro/caixas` | Fechamentos de caixa do período, com diferenças. |
| GET | `/api/relatorios/movimentacoes` | Movimentações do período (JSON). |
| GET | `/api/relatorios/movimentacoes.csv` | Movimentações do período (CSV para Excel). |
| GET | `/api/relatorios/recebimentos` | Recebimentos do período (JSON). |
| GET | `/api/relatorios/recebimentos.csv` | Recebimentos do período (CSV para Excel). |
| GET | `/api/relatorios/ocupacao` | Entradas por hora do dia e por dia da semana. |
| GET | `/api/configuracoes` | Ler configurações. |
| PUT | `/api/configuracoes` | Salvar configurações (cobrança, carência, dados do recibo). |
| GET | `/api/usuarios` | Listar usuários. |
| POST | `/api/usuarios` | Criar usuário com senha provisória. |
| POST | `/api/usuarios/<int:uid>/desativar` | Desativar usuário (mantém sempre um administrador ativo). |
| GET | `/api/auditoria` | Últimos 500 registros de auditoria. |
| POST | `/api/clientes/<int:cid>/ativo` | Ativar/desativar cliente (bloqueado com contrato vigente). Corpo: `{"ativo": true|false}`. |
| POST | `/api/veiculos/<int:vid>/ativo` | Ativar/desativar veículo (bloqueado com contrato vigente ou estacionado). |
| PUT | `/api/vagas/<int:vid>` | Editar número, tipo e plano (tipo/plano só com a vaga livre). |
| POST | `/api/vagas/<int:vid>/ativo` | Ativar/desativar vaga (bloqueado se ocupada ou se contratos dependem dela). |
| POST | `/api/movimentacoes/<int:movimentacao_id>/cancelar` | Cancelar entrada lançada por engano. Corpo: `{"motivo": "..."}` (mín. 5 caracteres). |
| POST | `/api/pagamentos/<int:pagamento_id>/cancelar` | Estornar recebimento (mensalidade volta a em aberto; horista fica cancelado) ou cancelar cobrança em aberto. Exige `motivo`; bloqueado se o caixa já foi fechado. |
| POST | `/api/usuarios/<int:uid>/redefinir-senha` | Gera senha provisória (aparece uma única vez na resposta). |
| POST | `/api/usuarios/<int:uid>/ativar` | Reativar usuário desativado. |

_71 rotas documentadas, mais as páginas HTML (`/`, `/login`, `/clientes`, `/historico`, `/financeiro`, `/relatorios` etc.)._
