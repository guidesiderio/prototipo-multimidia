# Aplicação Web Multimídia

Aplicação web para gerenciamento de objetos multimídia (imagens, áudios e
vídeos), desenvolvida na disciplina Tópicos em Engenharia de Software
(Computação em Nuvem), UFPI, turma 2026.1, Prof. Armando Soares Sousa.

## Status

1º protótipo (Avaliação 2), com a fundação da aplicação **implementada e
publicada na AWS**. Esta entrega cobre:

- Autenticação (registro, login, logout) e gerenciamento de perfil de usuário.
- Configuração de produção por variáveis de ambiente.
- Deploy em instância EC2 (Ubuntu 24.04) com Gunicorn + Nginx.

O upload de multimídia, o banco gerenciado (RDS) e o armazenamento de objetos
(S3) entram nos protótipos seguintes.

Aplicação publicada (protótipo, pode estar fora do ar para economizar free tier).
O IP muda quando a instância é parada e religada.

## Funcionalidades desta entrega

1. Registro de novos usuários (autentica logo após o cadastro).
2. Login e logout (logout via POST, exigência do Django 5).
3. Dashboard exibido após autenticação, com os dados e a foto do usuário.
4. Edição de perfil (nome completo, email, descrição e foto de perfil).
5. Alteração de senha mantendo a sessão ativa.
6. Painel administrativo do Django com a seção "Perfil" no usuário.

Cada usuário possui: nome completo, username, password, email, foto de perfil,
descrição e data de criação.

## Arquitetura

### Desenvolvimento (local)

```
Navegador  ->  runserver (Django)  ->  SQLite
```

### Produção (EC2)

```
Navegador  ->  Nginx (porta 80)  ->  Gunicorn (127.0.0.1:8000)  ->  Django  ->  SQLite
                  |
                  +--> /static/  (arquivos coletados por collectstatic)
                  +--> /media/   (uploads de foto de perfil)
```

- **Nginx**: proxy reverso na porta 80, serve `/static/` e `/media/` direto do disco.
- **Gunicorn**: servidor WSGI (3 workers), gerenciado pelo systemd (`gunicorn.service`),
  com início automático no boot e variáveis de produção via `EnvironmentFile`.

## Stack

- Python 3 e Django 5.2
- Gunicorn (WSGI em produção)
- Nginx (proxy reverso em produção)
- SQLite como banco de dados (será substituído por PostgreSQL/RDS em protótipo posterior)
- Pillow para o campo de imagem (`ImageField`)
- Templates do Django renderizados no servidor
- Ambiente isolado com venv

## Configuração por variáveis de ambiente

`config/settings.py` lê variáveis de ambiente, com padrões seguros para
desenvolvimento. Em produção elas vêm de um arquivo `.env` (fora do Git).

| Variável               | Padrão (dev)          | Função                                          |
| ---------------------- | --------------------- | ----------------------------------------------- |
| `DJANGO_SECRET_KEY`    | chave insegura de dev | Chave secreta do Django                         |
| `DJANGO_DEBUG`         | `True`                | Liga/desliga o modo debug (`False` em produção) |
| `DJANGO_ALLOWED_HOSTS` | `127.0.0.1,localhost` | Hosts permitidos, separados por vírgula         |

O arquivo `.env.example` na raiz documenta todas as variáveis (inclusive os
parâmetros de deploy e de criação do superusuário). Copie-o para `.env` e
preencha com valores reais:

```bash
cp .env.example .env
```

> O `.env` não é versionado (está no `.gitignore`), pois guarda a chave secreta
> e as credenciais.

## Pré-requisitos

- Python 3.10 ou superior
- Git

## Como executar localmente

```bash
# clonar o repositorio
git clone https://github.com/guidesiderio/prototipo-multimidia.git
cd prototipo-multimidia

# criar e ativar o ambiente virtual
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# instalar as dependencias
pip install -r requirements.txt

# aplicar as migracoes
python manage.py migrate

# criar um usuario administrador (opcional, para acessar o /admin)
python manage.py createsuperuser

# subir o servidor
python manage.py runserver
```

Acesse `http://127.0.0.1:8000/`. A raiz redireciona para o dashboard; sem login,
a aplicação leva para a tela de entrada.

Em desenvolvimento não é necessário definir variáveis de ambiente: os padrões do
`settings.py` já apontam para SQLite, `DEBUG=True` e hosts locais.

## Deploy em produção

O processo completo de implantação na EC2 (provisionamento, Gunicorn no systemd,
Nginx, verificação) está documentado em [`DEPLOY.md`](DEPLOY.md). Resumo:

1. Ajustes de produção no código (já aplicados em `config/settings.py`).
2. Provisionar a instância: `apt`, clone do repo, venv, `requirements.txt`.
3. `migrate`, `collectstatic`, `createsuperuser`.
4. Criar o `.env` de produção na instância.
5. Subir o serviço `gunicorn` (systemd) e configurar o Nginx na porta 80.

Reiniciar após mudança de código na instância:

```bash
git pull
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn
```

## Rotas principais

| Rota              | Descrição                       |
| ----------------- | ------------------------------- |
| `/`               | Redireciona para o dashboard    |
| `/registro/`      | Criação de conta                |
| `/login/`         | Autenticação                    |
| `/logout/`        | Encerrar sessão (POST)          |
| `/dashboard/`     | Painel do usuário autenticado   |
| `/perfil/editar/` | Edição dos dados do perfil      |
| `/perfil/senha/`  | Alteração de senha              |
| `/admin/`         | Painel administrativo do Django |

## Estrutura do projeto

```
.
├── config/                     # projeto Django
│   ├── settings.py             # configuracoes (lê variaveis de ambiente)
│   ├── urls.py                 # rotas do projeto + media em DEBUG
│   ├── wsgi.py                 # entrada WSGI usada pelo Gunicorn
│   └── asgi.py
├── usuarios/                   # app de autenticacao e perfil
│   ├── templates/usuarios/     # base, registro, login, dashboard,
│   │                           #   editar_perfil, alterar_senha
│   ├── migrations/             # 0001_initial (modelo Usuario)
│   ├── models.py               # modelo Usuario (estende AbstractUser)
│   ├── views.py                # registro, dashboard, editar_perfil
│   ├── forms.py                # RegistroForm, PerfilForm
│   ├── urls.py                 # rotas do app + views nativas de auth
│   └── admin.py                # UsuarioAdmin com secao "Perfil"
├── manage.py
├── requirements.txt
├── .env.example                # modelo de variaveis de ambiente
├── DEPLOY.md                   # runbook de implantacao na EC2
├── CLAUDE.md                   # especificacao do protótipo
└── README.md
```

O modelo de usuário é customizado (`usuarios.Usuario`, estendendo
`AbstractUser`), apontado por `AUTH_USER_MODEL` em `settings.py`. A autenticação
usa as views nativas do Django (`LoginView`, `LogoutView`, `PasswordChangeView`).

## Próximos passos

- Upload e gerenciamento de arquivos multimídia (imagens, áudios e vídeos).
- Armazenamento de objetos no S3.
- Banco gerenciado (RDS/PostgreSQL) no lugar do SQLite.
- HTTPS com certificado e domínio próprio.
- Monitoramento, balanceamento de carga e auto scaling.
