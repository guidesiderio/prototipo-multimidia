# Fase 4: Deploy da aplicação na EC2 (Ubuntu 24.04) — registro do que foi executado

> Este documento registra os passos **realmente executados** no deploy, que
> divergem em alguns pontos do runbook original. Principais diferenças:
>
> - Os comandos da EC2 foram rodados de forma **não interativa**, um a um, via
>   `ssh -i chave ubuntu@IP "comando"` (não houve sessão de login interativa).
> - A instalação de pacotes usou `apt-get` com `DEBIAN_FRONTEND=noninteractive`.
> - A **chave secreta de produção NÃO foi gerada na instância**: foi reaproveitada
>   a chave que já estava no arquivo `.env` local do projeto.
> - O **superusuário não foi `admin`**: foi criado a partir das variáveis
>   `DJANGO_SUPERUSER_*` do `.env` (usuário `guilhermedesiderio`).
> - Os valores reais (URL do repo, IP, chave, hosts, credenciais) vieram do
>   arquivo `.env` local, que serviu de fonte única de verdade do deploy.
>
> Cada comando indica onde roda: **LOCAL** (máquina de desenvolvimento) ou
> **EC2** (dentro da instância, via SSH não interativo).

## Pré-requisitos (já concluídos)

1. Instância EC2 com Ubuntu Server 24.04 (verificado: `Ubuntu 24.04.4 LTS`), IP público e SSH funcionando.
2. Security group liberando as portas 22 (SSH) e 80 (HTTP).
3. Aplicação Django no GitHub: projeto `config`, app `usuarios`, banco SQLite.
4. Chave `chave_prototipo.pem` disponível na raiz do projeto local.

## Valores reais usados

Estão todos no `.env` local (fora do Git). Os marcadores deste documento mapeiam para:

- Repositório: `guidesiderio/prototipo-multimidia`
- `IP_PUBLICO`: `98.92.219.104` (muda ao parar/religar a instância).
- Chave SSH: `chave_prototipo.pem` (na raiz do projeto local).
- `DJANGO_SECRET_KEY`: valor já presente no `.env` local (não impresso aqui).
- Superusuário: `DJANGO_SUPERUSER_USERNAME` / `_EMAIL` / `_PASSWORD` do `.env`.

> Segurança: a chave secreta e a senha do superusuário ficam só no `.env`
> (ignorado pelo Git). Não devem ser escritas neste arquivo nem commitadas.

## Parte A: ajustes de produção no código (LOCAL)

Edições aplicadas em `config/settings.py`:

No topo, abaixo de `from pathlib import Path`:

```python
import os
```

Logo abaixo da `SECRET_KEY` original (mantida como padrão de desenvolvimento):

```python
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", SECRET_KEY)
```

`DEBUG` trocado por:

```python
DEBUG = os.environ.get("DJANGO_DEBUG", "True") == "True"
```

`ALLOWED_HOSTS` trocado por:

```python
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
```

No fim do arquivo, destino dos estáticos:

```python
STATIC_ROOT = BASE_DIR / "staticfiles"
```

Observação: o `requirements.txt` já continha `gunicorn` (26.0.0), então o
`pip install gunicorn` do runbook original já estava satisfeito. O `.gitignore`
recebeu `*.pem` e `staticfiles/`. Em seguida, regenerou-se o lock e subiu-se:

```bash
# LOCAL
.venv/Scripts/python.exe -m pip freeze > requirements.txt
git add -A
git commit -m "Configuracao de producao: settings por variavel de ambiente, gunicorn e static"
git push
```

Validação local: `python manage.py check` retornou `System check identified no issues`.

## Parte B: provisionar e publicar na instância (EC2)

Todos os comandos abaixo rodaram via SSH não interativo, no formato:

```bash
# LOCAL
ssh -i "chave_prototipo.pem" -o BatchMode=yes ubuntu@98.92.219.104 "COMANDO"
```

A conexão foi validada primeiro com:

```bash
# LOCAL
ssh -i "chave_prototipo.pem" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 \
    -o BatchMode=yes ubuntu@98.92.219.104 "echo CONECTADO; whoami; lsb_release -d"
```

### B.1 Atualizar o sistema e instalar pacotes

```bash
# EC2 (não interativo)
sudo DEBIAN_FRONTEND=noninteractive apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv python3-pip git nginx
```

### B.2 Clonar o repositório e preparar o ambiente

A pasta foi removida antes para garantir um clone limpo, e o `pip` foi atualizado:

```bash
# EC2
cd ~
rm -rf prototipo-multimidia
git clone https://github.com/guidesiderio/prototipo-multimidia.git
cd prototipo-multimidia
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Repositório público, então o clone não pediu autenticação. Django instalado: 5.2.14.

### B.3 Migrar, juntar estáticos e criar o superusuário

A chave de desenvolvimento padrão atende a estes comandos de gerenciamento. O
superusuário foi criado a partir das variáveis do `.env` (não como `admin`):

```bash
# EC2 (com o venv ativo, dentro da pasta do projeto)
python manage.py migrate --noinput
python manage.py collectstatic --noinput
DJANGO_SUPERUSER_PASSWORD='<senha do .env>' python manage.py createsuperuser --noinput \
    --username guilhermedesiderio --email guilhermedesiderio23@gmail.com
```

Resultado: 20 migrações aplicadas, 127 arquivos estáticos copiados,
`Superuser created successfully`.

### B.4 Criar o `.env` de produção na instância

A chave secreta foi **copiada do `.env` local** (não gerada na instância):

```bash
# EC2 (dentro da pasta do projeto)
cat > .env <<EOF
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=98.92.219.104,127.0.0.1
DJANGO_SECRET_KEY=<chave do .env local>
EOF
chmod 600 .env
```

### B.5 Serviço do Gunicorn no systemd

```bash
# EC2
sudo tee /etc/systemd/system/gunicorn.service > /dev/null <<'EOF'
[Unit]
Description=Gunicorn para a aplicacao Django
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/prototipo-multimidia
EnvironmentFile=/home/ubuntu/prototipo-multimidia/.env
ExecStart=/home/ubuntu/prototipo-multimidia/.venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 config.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now gunicorn
systemctl is-active gunicorn
curl -s -I http://127.0.0.1:8000/ | head -1
```

`enable --now` faz start + enable num passo só. Status: `active`; o `curl`
retornou `HTTP/1.1 302 Found`.

> Sobre o `DJANGO_ALLOWED_HOSTS`: como o IP público muda ao parar/religar a
> instância, ao trocar o IP edite o `.env`, atualize essa linha e rode
> `sudo systemctl restart gunicorn`. Alternativa de menor atrito no protótipo:
> usar `*` no lugar do IP.

### B.6 Nginx como proxy reverso (porta 80)

A permissão da home e a pasta `media/` foram ajustadas junto com o Nginx:

```bash
# EC2
sudo tee /etc/nginx/sites-available/prototipo > /dev/null <<'EOF'
server {
    listen 80;
    server_name _;

    location /static/ {
        alias /home/ubuntu/prototipo-multimidia/staticfiles/;
    }

    location /media/ {
        alias /home/ubuntu/prototipo-multimidia/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/prototipo /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo chmod 755 /home/ubuntu
mkdir -p /home/ubuntu/prototipo-multimidia/media
sudo nginx -t
sudo systemctl restart nginx
```

`server_name _;` responde a qualquer host, então não quebra quando o IP muda.
`ln -sf` foi usado para ser idempotente. `nginx -t` retornou sintaxe ok.

## Parte C: verificação (resultados obtidos)

| Verificação | Comando | Resultado |
|---|---|---|
| Gunicorn ativo | `systemctl is-active gunicorn` | `active` |
| Sintaxe do Nginx | `sudo nginx -t` | syntax is ok |
| Porta 80 interna | `curl -I http://127.0.0.1/` (na EC2) | `302` |
| Admin | `curl http://127.0.0.1/admin/login/` (na EC2) | `200` |
| CSS estático | `curl http://127.0.0.1/static/admin/css/base.css` | `200` |
| Raiz externa | `curl http://98.92.219.104/` (do PC local) | `302` → `/dashboard/` |
| Login externo | `curl http://98.92.219.104/login/` | `200` |

Estáticos servidos pelo Nginx (CSS = 200), logo o `/admin/` aparece estilizado.

Falta apenas o teste manual no navegador (registro, login, edição de perfil com
upload de imagem e troca de senha) em `http://98.92.219.104`.

## Operação e custo

- Reiniciar após mudança de código: `git pull`, `pip install -r requirements.txt`, `python manage.py migrate`, `python manage.py collectstatic --noinput`, depois `sudo systemctl restart gunicorn`.
- Se o IP público mudar (após parar e religar): edite o `.env`, atualize `DJANGO_ALLOWED_HOSTS` (a menos que use `*`) e rode `sudo systemctl restart gunicorn`.
- Para economizar crédito do free tier, pare a instância quando não estiver testando ou apresentando. O IP muda na próxima vez que ligar.

## Solução de problemas

- `400 Bad Request`: o host de acesso não está em `DJANGO_ALLOWED_HOSTS`. Atualize a linha no `.env` e reinicie o Gunicorn.
- `502 Bad Gateway`: o Gunicorn não está respondendo. Veja `sudo systemctl status gunicorn` e `sudo journalctl -u gunicorn -n 50`.
- Admin sem estilo (CSS): `collectstatic` não rodou ou o Nginx não consegue ler a pasta. Rode `collectstatic`, confirme `sudo chmod 755 /home/ubuntu` e reinicie o Nginx.

## Fora de escopo desta fase

- HTTPS, certificado e domínio próprio.
- RDS, S3 e upload de multimídia.
- Auto scaling, balanceamento de carga e múltiplas instâncias.
