# Aplicação Web Multimídia

Aplicação web para gerenciamento de objetos multimídia (imagens, áudios e
vídeos), desenvolvida na disciplina Tópicos em Engenharia de Software
(Computação em Nuvem), UFPI, turma 2026.1, Prof. Armando Soares Sousa.

## Status

2º protótipo (Avaliação 3), com a aplicação **implementada e publicada na AWS**.
Esta entrega cobre:

- Autenticação (registro, login, logout) e gerenciamento de perfil de usuário.
- CRUD de objetos multimídia com busca, filtro por tipo e isolamento por usuário.
- Armazenamento dos binários (mídias e fotos de perfil) no **AWS S3**, em bucket
  privado com URLs assinadas e credenciais via IAM role.
- Configuração de produção por variáveis de ambiente.
- Deploy em instância EC2 (Ubuntu 24.04) com Gunicorn + Nginx.

O banco gerenciado (RDS/PostgreSQL) e o escalonamento horizontal (ALB, Auto
Scaling) entram nos protótipos seguintes.

Aplicação publicada (protótipo, pode estar fora do ar para economizar free tier).
O IP muda quando a instância é parada e religada.

## Funcionalidades desta entrega

1. Registro de novos usuários (autentica logo após o cadastro).
2. Login e logout (logout via POST, exigência do Django 5).
3. Dashboard exibido após autenticação, com os dados e a foto do usuário.
4. Edição de perfil (nome completo, email, descrição e foto de perfil).
5. Alteração de senha mantendo a sessão ativa.
6. CRUD de multimídia: criar, listar, visualizar/play, editar e excluir.
7. Busca por título/descrição e filtro por tipo (imagem, áudio, vídeo).
8. Isolamento por usuário: cada um só vê e acessa as próprias mídias (404 para mídia de outro).
9. Armazenamento dos binários no S3 (transparente para o código; alternável por toggle).
10. Painel administrativo do Django com a seção "Perfil" e o admin de mídias.

Cada usuário possui: nome completo, username, password, email, foto de perfil,
descrição e data de criação. Cada mídia possui: dono, título, descrição, tipo,
arquivo, data de criação e de atualização. O tipo é deduzido pela extensão no
upload (lista branca) e há teto de 50 MB por arquivo.

## Arquitetura

### Desenvolvimento (local)

```
Navegador  ->  runserver (Django)  ->  SQLite
                                   ->  disco (media/) para binarios
```

### Produção (EC2)

```
Navegador  ->  Nginx (porta 80)  ->  Gunicorn (127.0.0.1:8000)  ->  Django  ->  SQLite
                  |                                                     |
                  +--> /static/  (coletados por collectstatic)         +--> S3 (midias/, perfis/)
```

- **Nginx**: proxy reverso na porta 80, serve `/static/` direto do disco.
- **Gunicorn**: servidor WSGI (3 workers), gerenciado pelo systemd (`gunicorn.service`),
  com início automático no boot e variáveis de produção via `EnvironmentFile`.
- **S3**: binários de mídia e foto de perfil em bucket privado, servidos por URL
  assinada (validade de 1 hora), com credenciais pela IAM role da instância. Os
  estáticos seguem no disco, servidos pelo Nginx.

## Stack

- Python 3 e Django 5.2
- Gunicorn (WSGI em produção)
- Nginx (proxy reverso em produção)
- SQLite como banco de dados (será substituído por PostgreSQL/RDS em protótipo posterior)
- Pillow para o campo de imagem (`ImageField`)
- django-storages + boto3 para o armazenamento no S3
- Templates do Django renderizados no servidor
- Ambiente isolado com venv

## Configuração por variáveis de ambiente

`config/settings.py` lê variáveis de ambiente, com padrões seguros para
desenvolvimento. Em produção elas vêm de um arquivo `.env` (fora do Git).

| Variável                  | Padrão (dev)          | Função                                            |
| ------------------------- | --------------------- | ------------------------------------------------- |
| `DJANGO_SECRET_KEY`       | chave insegura de dev | Chave secreta do Django                           |
| `DJANGO_DEBUG`            | `True`                | Liga/desliga o modo debug (`False` em produção)   |
| `DJANGO_ALLOWED_HOSTS`    | `127.0.0.1,localhost` | Hosts permitidos, separados por vírgula           |
| `USE_S3`                  | `False`               | Liga o storage no S3 (`True` em produção)         |
| `AWS_STORAGE_BUCKET_NAME` | (vazio)               | Nome do bucket S3 (só usado quando `USE_S3=True`) |
| `AWS_S3_REGION_NAME`      | `us-east-1`           | Região do bucket                                  |

Com `USE_S3=False` (padrão), os binários ficam no disco em `media/` e nada toca o
S3 — desenvolvimento e testes rodam sem credenciais AWS. Em produção não há
chaves de acesso no `.env`: o boto3 usa a IAM role anexada à EC2.

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
`settings.py` já apontam para SQLite, `DEBUG=True`, hosts locais e storage em
disco (`USE_S3=False`).

Para rodar os testes do app de mídias:

```bash
python manage.py test midias
```

## Deploy em produção

O processo completo de implantação na EC2 (provisionamento, Gunicorn no systemd,
Nginx, verificação) está documentado em [`DEPLOY.md`](DEPLOY.md). Resumo:

1. Ajustes de produção no código (já aplicados em `config/settings.py`).
2. Provisionar a instância: `apt`, clone do repo, venv, `requirements.txt`.
3. `migrate`, `collectstatic`, `createsuperuser`.
4. Criar o `.env` de produção na instância (incluindo `USE_S3=True` e o bucket).
5. Subir o serviço `gunicorn` (systemd) e configurar o Nginx na porta 80.

A configuração da AWS para o S3 (bucket privado, política IAM de menor
privilégio, role anexada à EC2) e o passo a passo de deploy/validação estão nos
documentos da pasta [`docs/`](docs/): `PROTOTIPO_2_S3.md` e
`PROTOTIPO_2_S3_DEPLOY_EC2.md`.

Reiniciar após mudança de código na instância:

```bash
git pull
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn
```

## Rotas principais

| Rota                     | Descrição                            |
| ------------------------ | ------------------------------------ |
| `/`                      | Redireciona para o dashboard         |
| `/registro/`             | Criação de conta                     |
| `/login/`                | Autenticação                         |
| `/logout/`               | Encerrar sessão (POST)               |
| `/dashboard/`            | Painel do usuário autenticado        |
| `/perfil/editar/`        | Edição dos dados do perfil           |
| `/perfil/senha/`         | Alteração de senha                   |
| `/midias/`               | Lista das mídias do usuário (busca/filtro) |
| `/midias/nova/`          | Upload de nova mídia                 |
| `/midias/<pk>/`          | Detalhe com visualização/play        |
| `/midias/<pk>/editar/`   | Edição de título e descrição         |
| `/midias/<pk>/excluir/`  | Confirmação e exclusão               |
| `/admin/`                | Painel administrativo do Django      |

## Estrutura do projeto

```
.
├── config/                     # projeto Django
│   ├── settings.py             # configuracoes (lê variaveis de ambiente; bloco USE_S3/STORAGES)
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
├── midias/                     # app de multimidia (CRUD)
│   ├── templates/midias/       # lista, detalhe, form, confirmar_exclusao
│   ├── migrations/             # 0001_initial (modelo Midia)
│   ├── models.py               # modelo Midia (tipo, dono, arquivo)
│   ├── views.py                # lista, detalhe, criar, editar, excluir
│   ├── forms.py                # MidiaCriarForm, MidiaEditarForm
│   ├── urls.py                 # rotas do app (namespace "midias")
│   ├── admin.py                # MidiaAdmin
│   └── tests.py                # isolamento, validacao de upload, busca
├── docs/                       # documentos de implementacao do Protótipo 2
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
A multimídia usa o modelo único `midias.Midia`, com `tipo` deduzido pela extensão
e isolamento por `dono`.

## Próximos passos

- Banco gerenciado (RDS/PostgreSQL) no lugar do SQLite.
- Escalonamento horizontal: Launch Template, ALB e Auto Scaling.
- HTTPS com certificado e domínio próprio.
- Monitoramento, balanceamento de carga e auto scaling.
