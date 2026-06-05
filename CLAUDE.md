# Protótipo 1: Fundação da Aplicação Web Multimídia

> Briefing do estado atual da aplicação. Descreve o que já está implementado e
> publicado: autenticação, perfil de usuário, configuração de produção e deploy
> na AWS EC2. Serve de referência para quem continua o projeto e para orientar
> as próximas etapas (upload de multimídia, RDS, S3).

## 1. Contexto

Disciplina: Tópicos em Engenharia de Software (Computação em Nuvem), UFPI, turma
2026.1, Prof. Armando Soares Sousa. Avaliação 2, 1º protótipo. Projeto em equipe.

A aplicação web final gerencia objetos multimídia (imagens, áudios e vídeos).
Neste 1º protótipo o foco foi a fundação: autenticação e perfil de usuário.
Upload de multimídia, S3 e RDS entram em protótipos posteriores.

## 2. Decisões técnicas (fechadas, não alterar)

* Framework: Django 5.2.
* Banco de dados: SQLite neste protótipo (PostgreSQL/RDS fica para depois).
* Isolamento de dependências: venv. Sem Docker.
* Código e comentários em português do Brasil.
* Projeto Django chamado `config`. App principal chamado `usuarios`.
* Modelo de usuário customizado estendendo `AbstractUser`.
* Autenticação com as views nativas do Django (`LoginView`, `LogoutView`, `PasswordChangeView`).
* Templates renderizados no servidor, estilizados com Bootstrap 5.3 (via CDN) e CSS próprio.

## 3. Estado atual (implementado e publicado)

Funcionalidades em produção:

1. **Registro** de novos usuários, com autenticação automática logo após o cadastro.
2. **Login e logout** (logout via POST, exigência do Django 5).
3. **Dashboard** exibido após autenticação, com os dados e a foto do usuário e o
   menu de navegação.
4. **Edição de perfil**: nome completo, email, descrição e foto de perfil.
5. **Alteração de senha** mantendo a sessão ativa.
6. **Painel administrativo** do Django com a seção "Perfil" no usuário.

Estado da publicação:

* Aplicação publicada em instância **EC2 (Ubuntu 24.04)** com **Gunicorn + Nginx**.
* Configuração de produção por variáveis de ambiente (`.env` na instância, fora do Git).
* O IP público muda ao parar/religar a instância; a instância pode ficar fora do
  ar para economizar free tier. Runbook completo em [`DEPLOY.md`](DEPLOY.md).

Modelo de usuário (`usuarios.Usuario`, estende `AbstractUser`), apontado por
`AUTH_USER_MODEL`. Campos: nome completo, username, password, email, foto de
perfil, descrição e data de criação (`date_joined`).

## 4. Arquitetura

### Desenvolvimento (local)

```
Navegador  ->  runserver (Django)  ->  SQLite
```

### Produção (EC2)

```
Navegador  ->  Nginx (porta 80)  ->  Gunicorn (127.0.0.1:8000)  ->  Django  ->  SQLite
                  |
                  +--> /static/  (coletados por collectstatic)
                  +--> /media/   (uploads de foto de perfil)
```

* **Nginx**: proxy reverso na porta 80; serve `/static/` e `/media/` direto do disco.
* **Gunicorn**: WSGI (3 workers), gerenciado pelo systemd, início no boot e
  variáveis de produção via `EnvironmentFile`.

## 5. Configuração por variáveis de ambiente

`config/settings.py` lê variáveis de ambiente com padrões seguros para
desenvolvimento. Em produção elas vêm do `.env` na instância.

| Variável               | Padrão (dev)          | Função                                          |
| ---------------------- | --------------------- | ----------------------------------------------- |
| `DJANGO_SECRET_KEY`    | chave insegura de dev | Chave secreta do Django                         |
| `DJANGO_DEBUG`         | `True`                | Liga/desliga o modo debug (`False` em produção) |
| `DJANGO_ALLOWED_HOSTS` | `127.0.0.1,localhost` | Hosts permitidos, separados por vírgula         |

`.env.example` documenta todas as variáveis (inclusive parâmetros de deploy e de
criação do superusuário). O `.env` não é versionado (está no `.gitignore`).

Enquanto a aplicação for protótipo, o `.env` da EC2 usa `DJANGO_ALLOWED_HOSTS=*`
para evitar reconfigurar a cada troca de IP. É permissivo; ao ter domínio ou IP
fixo, trocar por lista explícita.

## 6. Estrutura do projeto

```
.
├── config/                     # projeto Django
│   ├── settings.py             # configuracoes (lê variaveis de ambiente)
│   ├── urls.py                 # rotas do projeto + media em DEBUG
│   ├── wsgi.py                 # entrada WSGI usada pelo Gunicorn
│   └── asgi.py
├── usuarios/                   # app de autenticacao e perfil
│   ├── static/usuarios/        # estilo.css (estilos proprios)
│   ├── templates/usuarios/     # base, registro, login, dashboard,
│   │                           #   editar_perfil, alterar_senha, _campos_form
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
├── README.md
└── CLAUDE.md                   # este briefing
```

## 7. Rotas principais

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

A raiz redireciona para o dashboard; sem login, o `login_required` leva à tela
de entrada.

## 8. Convenções de código

* Nomes de modelos, campos e funções em português quando fizer sentido.
* Comentários curtos e só onde agregam; nada de comentário óbvio.
* Seguir o estilo padrão do Django e o PEP 8.
* Manter a estilização via Bootstrap (CDN) + `estilo.css`; templates herdam de
  `base.html`, que já traz a navbar e o bloco de mensagens.

## 9. Próximos passos (fora do escopo deste protótipo)

* Upload e gerenciamento de arquivos multimídia (imagens, áudios e vídeos).
* Armazenamento de objetos no S3.
* Banco gerenciado (RDS/PostgreSQL) no lugar do SQLite. O driver `psycopg` já
  consta em `requirements.txt`, antecipando essa migração.
* Infraestrutura AWS completa: VPC, grupos de segurança, tabela de rotas.
* HTTPS com certificado e domínio próprio.
* Monitoramento, balanceamento de carga e auto scaling.
