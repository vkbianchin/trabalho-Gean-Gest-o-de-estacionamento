# Colocando o ParkFlow em uma VPS (Ubuntu/Debian)

Roteiro de referência. **Não foi executado em um servidor real**: ajuste nomes, caminhos e domínio ao seu caso e teste primeiro em uma máquina descartável.

## 1. Servidor
```bash
sudo apt update && sudo apt install -y python3 python3-venv nginx mariadb-server certbot python3-certbot-nginx ufw
sudo ufw allow OpenSSH && sudo ufw allow "Nginx Full" && sudo ufw enable   # só SSH, 80 e 443 abertos
sudo adduser --system --group --home /opt/parkflow parkflow
```
Use **acesso SSH por chave** e desative a senha (`PasswordAuthentication no` em `/etc/ssh/sshd_config`).

## 2. Banco
```bash
sudo mysql_secure_installation
sudo mysql -e "CREATE DATABASE estacionamento CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
sudo mysql < scripts/permissoes_mysql.sql      # antes, troque a senha e o nome do banco no arquivo
sudo mysql estacionamento < banco/schema.sql   # instalação nova (veja banco/README.md para bancos existentes)
```
O MariaDB deve aceitar conexões **apenas locais** (`bind-address = 127.0.0.1`).

## 3. Aplicação
```bash
sudo -u parkflow git clone <seu-repositorio> /opt/parkflow/app
cd /opt/parkflow/app
sudo -u parkflow python3 -m venv venv && sudo -u parkflow venv/bin/pip install -r requirements-prod.txt
sudo -u parkflow cp .env.example .env && sudo chmod 600 .env && sudo chown parkflow:parkflow .env
sudo -u parkflow nano .env       # SECRET_KEY nova, DB_*, SESSION_COOKIE_SECURE=1, TRUST_PROXY=1
sudo -u parkflow venv/bin/python -m scripts.criar_primeiro_usuario
sudo -u parkflow venv/bin/python -m scripts.dados_iniciais
```
O `.env` fica só no servidor, com permissão `600`. **Nunca** o envie em zip, e-mail ou Git.

## 4. Serviço e nginx
```bash
sudo cp deploy/parkflow.service /etc/systemd/system/ && sudo systemctl daemon-reload
sudo systemctl enable --now parkflow
sudo cp deploy/nginx-parkflow.conf /etc/nginx/sites-available/parkflow    # troque seu-dominio.com.br
sudo ln -s /etc/nginx/sites-available/parkflow /etc/nginx/sites-enabled/ && sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d seu-dominio.com.br        # HTTPS gratuito (Let's Encrypt)
```
Teste: `curl https://seu-dominio.com.br/saude` deve responder `{"banco":true,"status":"ok"}`.

## 5. Backup
```bash
sudo cp deploy/backup_mysql.sh /usr/local/bin/ && sudo chmod 700 /usr/local/bin/backup_mysql.sh
echo "30 2 * * * root /usr/local/bin/backup_mysql.sh" | sudo tee /etc/cron.d/parkflow-backup
```
Copie os arquivos de `/var/backups/parkflow` para **outro lugar** (outro servidor ou armazenamento na nuvem) e **teste a restauração** pelo menos uma vez.

## 6. Atualizar a versão
1. Backup (`sudo backup_mysql.sh`).
2. `git pull` e aplicar as migrações novas de `banco/migracoes/` **antes** de reiniciar.
3. `sudo systemctl restart parkflow` e conferir `/saude` e o log em `logs/estacionamento.log`.

## Lista de conferência
- [ ] Senhas do banco e do SSH novas (nunca reutilize as de desenvolvimento)
- [ ] `FLASK_SECRET_KEY` nova e `SESSION_COOKIE_SECURE=1`
- [ ] HTTPS ativo e redirecionando de HTTP
- [ ] Firewall com só 22, 80 e 443
- [ ] Backup diário agendado, cópia fora do servidor e restauração testada
- [ ] Usuário de demonstração com dados fictícios, se o sistema for exibido publicamente
