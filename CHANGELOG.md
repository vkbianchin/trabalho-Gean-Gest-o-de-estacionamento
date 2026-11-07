# Histórico de mudanças

## 3.1 — manutenção, cancelamentos e segurança

**Novidades**
- **Editar e ativar/desativar** clientes, veículos e vagas, com travas: não desativa vaga ocupada, nem cliente/veículo com contrato vigente, nem vaga mensal de que contratos dependem; tipo/plano da vaga só mudam com ela livre. CPF/CNPJ, placa e dono não mudam.
- **Cancelar entrada** lançada por engano (libera a vaga) e **estornar pagamentos**, com motivo obrigatório e auditoria. Mensalidade estornada volta para "em aberto"; caixa já fechado não é alterado. Canceladas ficam fora dos relatórios e do financeiro.
- **Usuários:** redefinir senha (senha provisória mostrada uma vez) e reativar.
- **Verificação em duas etapas (TOTP)** compatível com Google/Microsoft Authenticator e Authy, em `Minha conta > Segurança da conta`. Implementada com a biblioteca padrão e testada com os vetores do RFC 6238.
- **Preferências de aparência salvas por usuário** (migração 005).
- Caixas de confirmação e de motivo no lugar do `confirm()` do navegador.

**Correções**
- Os botões **Cancelar** e **×** das janelas não fechavam (o clique era interrompido antes do fechamento); agora fecham, e a tecla Esc também.

**Organização**
- `app.js` dividido: `nucleo.js` + um arquivo por tela em `static/js/telas/` (carregado só na página que usa).
- Migrações `005` e `006`; `schema.sql` atualizado.
- Teste de **integração com MariaDB real** (`tests/integracao/`) e job `banco-real` na CI.
- Testes: de 142 para 219 (mais um módulo de integração que só roda com banco).

## 3.0 — versão para portfólio

**Novidades**
- **Financeiro** (somente administrador): recebido por período, forma de pagamento, origem e dia; ticket médio; permanência média; inadimplência; fechamentos de caixa com diferença.
- **Relatórios** (somente administrador): movimentações, recebimentos e horários de pico, com exportação CSV para Excel (protegida contra injeção de fórmula).
- **Configurações**: carência de atraso, dados do estabelecimento (razão social, CNPJ, endereço, telefone) e auditoria das alterações. Os campos de preço que apareciam e não faziam nada foram removidos (os preços ficam em Catálogos > Preços).
- **Histórico por veículo** (`/historico`): todas as passagens de uma placa com totais; link também na lista de veículos.
- **Saída com tempo total estacionado**: prévia antes de confirmar (entrada, tempo, tolerância, valor) e resumo depois de registrar, com botão de recibo.
- **Recibo imprimível** de pagamentos recebidos, com CPF/CNPJ do cliente ou informado na hora.
- **Clientes pessoa física ou jurídica**, validação de CNPJ, máscara e preenchimento de endereço pelo CEP.
- **Tipo da vaga (carro/moto)** visível nas vagas, com filtro; na entrada, só aparecem as vagas do tipo escolhido.
- **Mensalidade em atraso** avisada na entrada do veículo mensalista.
- **Regra do `@`:** só é aceito no campo de e-mail (no navegador e no servidor).
- Rota `/saude` para monitoramento.

**Correções**
- **Datas na tela:** a API devolvia as datas no formato HTTP (`Fri, 30 Oct 2026 10:00:00 GMT`). Reproduzindo o código da tela, os horários apareciam como esse texto bruto e as datas de vencimento/competência como datas erradas (ex.: 30/10/2001). Agora a API devolve ISO 8601 em horário de Brasília e as telas formatam corretamente.
- **Voltar do navegador:** depois do login, a tela de login não reaparece; depois do logout, telas internas não reabrem (páginas sem cache, redirecionamento e conferência ao restaurar a página).
- **Usuário desativado** (ou rebaixado) perde o acesso na próxima requisição, não só quando o cookie expira.
- Auditoria de criação de cliente, veículo e usuário e de desativação de usuário.
- Coluna de placa nos pagamentos de horistas.

**Segurança e operação**
- Cabeçalhos de segurança (CSP, nosniff, anti-frame, HSTS quando HTTPS) e `no-store` nas páginas e APIs.
- Suporte a proxy reverso (`TRUST_PROXY`), exemplos de `systemd`, `nginx` e backup em `deploy/`.
- `.env.example`, `.gitignore` completo, pacote sem `venv`, `.env` nem logs.

**Banco** — migrações novas `003` (pessoa física/jurídica) e `004` (configurações); `schema.sql` e `scripts/exportar_schema.py`.

**Testes** — de 45 para 140+ testes (documentos, duração, CSV, saída, histórico, atraso, configurações, cadastro PF/PJ, relatórios, recibo, cabeçalhos e revalidação de sessão). Integração contínua em `.github/workflows/ci.yml`.

## Versões anteriores

Resumo das correções antigas em `docs/historico/`.
