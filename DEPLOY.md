# Fase 4: Deploy da aplicação na EC2 (Ubuntu 24.04)

> Runbook de implantação para o Claude Code executar. A Fase 4 tem duas frentes,
> e cada comando indica onde roda: **LOCAL** (máquina de desenvolvimento, onde
> está o repositório) ou **EC2** (dentro da instância, via SSH). A Parte A roda
> local; as Partes B e C rodam na instância.

## Pré-requisitos (já concluídos)

1. Instância EC2 com Ubuntu Server 24.04, IP público e acesso por SSH funcionando.
2. Security group liberando as portas 22 (SSH) e 80 (HTTP).
3. Aplicação Django no GitHub: projeto `config`, app `usuarios`, banco SQLite.
4. Chave `.pem` para SSH disponível na máquina local.

## Valores a substituir antes de executar

Troque estes marcadores ao longo do documento pelos valores reais:

- `SEU_USUARIO/SEU_REPO`: caminho do repositório no GitHub.
- `SEU_REPO`: nome da pasta do repositório (igual ao nome do repo).
- `IP_PUBLICO`: IP público atual da instância (exemplo `98.92.219.104`). Ele muda quando a instância é parada e religada.
- `CAMINHO_CHAVE.pem`: caminho do arquivo de chave SSH na máquina local.
- `COLE_A_CHAVE_GERADA`: chave secreta de produção gerada na Parte B.
- `UMA_SENHA_FORTE`: senha do superusuário a ser criado.

## Parte A: ajustes de produção no código (LOCAL)

Edite `config/settings.py`.

No topo do arquivo, logo abaixo de `from pathlib import Path`, adicione:

```python
import os
```

Logo abaixo da linha existente `SECRET_KEY = "django-insecure-..."`, acrescente
(mantendo a original como padrão de desenvolvimento):

```python
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", SECRET_KEY)
```

Troque a linha do `DEBUG` por:

```python
DEBUG = os.environ.get("DJANGO_DEBUG", "True") == "True"
```

Troque a linha do `ALLOWED_HOSTS` por:

```python
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
```

No fim do arquivo, adicione o destino dos arquivos estáticos:

```python
STATIC_ROOT = BASE_DIR / "staticfiles"
```

Adicione o Gunicorn às dependências e suba para o Git:

```bash
# LOCAL
pip install gunicorn
pip freeze > requirements.txt
git add .
git commit -m "Configuracao de producao: settings por variavel de ambiente, gunicorn e static"
git push
```

## Parte B: provisionar e publicar na instância (EC2)

Conecte na instância (LOCAL):

```bash
# LOCAL
ssh -i CAMINHO_CHAVE.pem ubuntu@IP_PUBLICO
```

A partir daqui, todos os comandos rodam dentro da instância.

Atualize o sistema e instale Python, Git e Nginx:

```bash
# EC2
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-venv python3-pip git nginx
```

Clone o repositório e prepare o ambiente:

```bash
# EC2
git clone https://github.com/SEU_USUARIO/SEU_REPO.git
cd SEU_REPO
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Se o repositório for privado, o clone vai pedir autenticação. Use um token de
acesso pessoal do GitHub ou deixe o repositório público durante esta fase.

Gere a chave secreta de produção e copie o resultado; ele vai no arquivo `.env`
da instância logo adiante:

```bash
# EC2
python3 -c 'import secrets; print(secrets.token_urlsafe(50))'
```

Aplique as migrações, junte os estáticos e crie o superusuário. Estes comandos de
gerenciamento usam a chave de desenvolvimento padrão, então não precisam das
variáveis de ambiente de produção:

```bash
# EC2 (com o venv ativo, dentro da pasta do projeto)
python manage.py migrate
python manage.py collectstatic --noinput
DJANGO_SUPERUSER_PASSWORD='UMA_SENHA_FORTE' python manage.py createsuperuser --noinput --username admin --email admin@example.com
```

Crie o arquivo de ambiente da aplicação na instância, com as variáveis de
produção. Ele fica fora do Git (já está no `.gitignore`) e guarda a chave
secreta. Substitua `IP_PUBLICO` e `COLE_A_CHAVE_GERADA` pelos valores reais:

```bash
# EC2 (dentro da pasta do projeto)
cat > .env <<EOF
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=IP_PUBLICO,127.0.0.1
DJANGO_SECRET_KEY=COLE_A_CHAVE_GERADA
EOF
chmod 600 .env
```

Crie o serviço do Gunicorn no systemd apontando para esse arquivo de ambiente.
Assim nenhum segredo fica escrito dentro do serviço. Substitua `SEU_REPO` pelo
nome real da pasta do repositório:

```bash
# EC2
sudo tee /etc/systemd/system/gunicorn.service > /dev/null <<'EOF'
[Unit]
Description=Gunicorn para a aplicacao Django
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/SEU_REPO
EnvironmentFile=/home/ubuntu/SEU_REPO/.env
ExecStart=/home/ubuntu/SEU_REPO/.venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 config.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
EOF
```

Sobre o `DJANGO_ALLOWED_HOSTS`: como o IP público muda quando a instância é
parada e religada, ao mudar o IP você edita o `.env`, atualiza essa linha e
reinicia o Gunicorn. Alternativa de menor atrito durante o protótipo: usar `*`
no lugar do IP, que aceita qualquer host. É uma flexibilização aceitável só por
ser um protótipo de curta duração; em produção real se usa o domínio ou IP
exato.

Suba e habilite o serviço:

```bash
# EC2
sudo systemctl daemon-reload
sudo systemctl start gunicorn
sudo systemctl enable gunicorn
sudo systemctl status gunicorn
```

O status deve aparecer como `active (running)`. Teste o Gunicorn localmente:

```bash
# EC2
curl -I http://127.0.0.1:8000/
```

Deve retornar `HTTP/1.1 302 Found`.

Configure o Nginx como proxy reverso na porta 80. Substitua `SEU_REPO` pelo nome
real da pasta do repositório:

```bash
# EC2
sudo tee /etc/nginx/sites-available/prototipo > /dev/null <<'EOF'
server {
    listen 80;
    server_name _;

    location /static/ {
        alias /home/ubuntu/SEU_REPO/staticfiles/;
    }

    location /media/ {
        alias /home/ubuntu/SEU_REPO/media/;
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
```

O `server_name _;` faz o Nginx responder a qualquer host, então ele não quebra
quando o IP da instância muda.

Habilite o site, remova o site padrão, valide e reinicie:

```bash
# EC2
sudo ln -s /etc/nginx/sites-available/prototipo /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

Garanta que o Nginx (usuário `www-data`) consegue atravessar a pasta home para
ler os estáticos:

```bash
# EC2
sudo chmod 755 /home/ubuntu
mkdir -p /home/ubuntu/SEU_REPO/media
```

## Parte C: verificação

A aplicação está publicada quando:

1. `sudo systemctl status gunicorn` mostra `active (running)`.
2. `sudo nginx -t` retorna sintaxe ok.
3. `curl -I http://127.0.0.1/` na instância retorna `302`.
4. No navegador, `http://IP_PUBLICO` abre a aplicação e redireciona para a tela de login.
5. O `/admin/` carrega com o CSS aplicado (sinal de que os estáticos estão sendo servidos).
6. Registro, login, dashboard, edição de perfil (com upload de imagem) e troca de senha funcionam pelo navegador.

## Operação e custo

- Reiniciar após mudança de código: `git pull`, `pip install -r requirements.txt`, `python manage.py migrate`, `python manage.py collectstatic --noinput`, depois `sudo systemctl restart gunicorn`.
- Se o IP público mudar (após parar e religar a instância): edite o `.env`, atualize `DJANGO_ALLOWED_HOSTS` (a menos que esteja usando `*`) e rode `sudo systemctl restart gunicorn`.
- Para economizar crédito do free tier, pare a instância quando não estiver testando ou apresentando. O IP vai mudar na próxima vez que ligar.

## Solução de problemas

- `400 Bad Request`: o host de acesso não está em `DJANGO_ALLOWED_HOSTS`. Atualize a linha no arquivo `.env` e reinicie o Gunicorn.
- `502 Bad Gateway`: o Gunicorn não está respondendo. Veja `sudo systemctl status gunicorn` e `sudo journalctl -u gunicorn -n 50`.
- Admin sem estilo (CSS): `collectstatic` não rodou ou o Nginx não consegue ler a pasta. Rode `collectstatic`, confirme o `sudo chmod 755 /home/ubuntu` e reinicie o Nginx.

## Fora de escopo desta fase

- HTTPS, certificado e domínio próprio.
- RDS, S3 e upload de multimídia.
- Auto scaling, balanceamento de carga e múltiplas instâncias.
