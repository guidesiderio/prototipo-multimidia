# Protótipo 2: Multimídia e Armazenamento de Objetos no S3

> Briefing do estado atual da aplicação. Descreve o que já está implementado e
> publicado: autenticação e perfil (Protótipo 1), CRUD de objetos multimídia com
> isolamento por usuário, e armazenamento dos binários no AWS S3 com URLs
> assinadas via IAM role. Serve de referência para quem continua o projeto e para
> orientar as próximas etapas (RDS, escalonamento horizontal).

## 1. Contexto

Disciplina: Tópicos em Engenharia de Software (Computação em Nuvem), UFPI, turma
2026.1, Prof. Armando Soares Sousa. Projeto em equipe.

A aplicação web gerencia objetos multimídia (imagens, áudios e vídeos). O 1º
protótipo (Avaliação 2) entregou a fundação: autenticação e perfil de usuário. O
2º protótipo (Avaliação 3) adiciona o CRUD de multimídia e o armazenamento dos
binários no S3. RDS/PostgreSQL e escalonamento (ALB, Auto Scaling) ficam para
fases posteriores.

## 2. Decisões técnicas (fechadas, não alterar)

* Framework: Django 5.2.
* Banco de dados: SQLite neste protótipo (PostgreSQL/RDS fica para depois).
* Isolamento de dependências: venv. Sem Docker.
* Código e comentários em português do Brasil.
* Projeto Django chamado `config`. Apps: `usuarios` (auth/perfil) e `midias` (multimídia).
* Modelo de usuário customizado estendendo `AbstractUser`.
* Autenticação com as views nativas do Django (`LoginView`, `LogoutView`, `PasswordChangeView`).
* Multimídia com **modelo único `Midia`** e campo `tipo` (imagem, áudio, vídeo) deduzido pela extensão.
* Templates renderizados no servidor, estilizados com Bootstrap 5.3 (via CDN) e CSS próprio.
* Storage de binários alternável por toggle `USE_S3`: disco local em dev, S3 em produção.

## 3. Estado atual (implementado e publicado)

Funcionalidades em produção:

1. **Registro** de novos usuários, com autenticação automática logo após o cadastro.
2. **Login e logout** (logout via POST, exigência do Django 5).
3. **Dashboard** exibido após autenticação, com os dados e a foto do usuário e o menu de navegação.
4. **Edição de perfil**: nome completo, email, descrição e foto de perfil.
5. **Alteração de senha** mantendo a sessão ativa.
6. **CRUD de multimídia**: criar, listar, visualizar/play, editar e excluir mídias.
7. **Busca e filtro** de mídias por título/descrição (`q`) e por tipo.
8. **Isolamento por usuário**: cada usuário só vê e acessa as próprias mídias (404 para mídia de outro).
9. **Armazenamento no S3**: mídias e fotos de perfil gravadas em bucket privado, com URLs assinadas.
10. **Painel administrativo** do Django com a seção "Perfil" no usuário e o admin de `Midia`.

Estado da publicação:

* Aplicação publicada em instância **EC2 (Ubuntu 24.04)** com **Gunicorn + Nginx**.
* Configuração de produção por variáveis de ambiente (`.env` na instância, fora do Git).
* Binários (mídias e fotos) no **bucket S3 privado** `prototipo-multimidia-midias-topicos-engenharia`
  (`us-east-1`), com credenciais via **IAM role** anexada à instância (sem chaves no `.env`).
* O IP público muda ao parar/religar a instância; a instância pode ficar fora do
  ar para economizar free tier. Runbook completo em [`DEPLOY.md`](DEPLOY.md).

Modelo de usuário (`usuarios.Usuario`, estende `AbstractUser`), apontado por
`AUTH_USER_MODEL`. Campos: nome completo, username, password, email, foto de
perfil (`upload_to="perfis/"`), descrição e data de criação (`date_joined`).

Modelo de mídia (`midias.Midia`): `dono` (FK para o usuário), `titulo`,
`descricao`, `tipo` (imagem/áudio/vídeo), `arquivo` (`FileField`,
`upload_to="midias/"`), `criado_em`, `atualizado_em`. O `tipo` é deduzido pela
extensão no upload e validado contra lista branca; teto de 50 MB por arquivo. A
edição mexe só em título e descrição; o binário não é trocado.

## 4. Arquitetura

### Desenvolvimento (local)

```
Navegador  ->  runserver (Django)  ->  SQLite
                                   ->  disco (media/) para binarios
```

### Produção (EC2)

```
Navegador  ->  Nginx (porta 80)  ->  Gunicorn (127.0.0.1:8000)  ->  Django  ->  SQLite
                  |                                                     |
                  +--> /static/  (coletados por collectstatic)         +--> S3 (binarios: midias/, perfis/)
```

* **Nginx**: proxy reverso na porta 80; serve `/static/` direto do disco.
* **Gunicorn**: WSGI (3 workers), gerenciado pelo systemd, início no boot e
  variáveis de produção via `EnvironmentFile`.
* **S3**: binários de mídia e foto de perfil em bucket privado; servidos por URL
  assinada (querystring auth, validade 1 hora). Os estáticos seguem no disco,
  servidos pelo Nginx, compatíveis com múltiplas instâncias idênticas.

## 5. Configuração por variáveis de ambiente

`config/settings.py` lê variáveis de ambiente com padrões seguros para
desenvolvimento. Em produção elas vêm do `.env` na instância.

| Variável                  | Padrão (dev)          | Função                                              |
| ------------------------- | --------------------- | --------------------------------------------------- |
| `DJANGO_SECRET_KEY`       | chave insegura de dev | Chave secreta do Django                             |
| `DJANGO_DEBUG`            | `True`                | Liga/desliga o modo debug (`False` em produção)     |
| `DJANGO_ALLOWED_HOSTS`    | `127.0.0.1,localhost` | Hosts permitidos, separados por vírgula             |
| `USE_S3`                  | `False`               | Liga o storage no S3 (`True` em produção)           |
| `AWS_STORAGE_BUCKET_NAME` | (vazio)               | Nome do bucket S3 (só usado quando `USE_S3=True`)   |
| `AWS_S3_REGION_NAME`      | `us-east-1`           | Região do bucket                                    |

Quando `USE_S3` é falso, o `STORAGES` não é definido e o Django usa o disco
(padrão), então dev e testes não tocam no S3. Não há `AWS_ACCESS_KEY_ID` nem
`AWS_SECRET_ACCESS_KEY`: em produção o boto3 obtém as credenciais da IAM role da
instância.

`.env.example` documenta todas as variáveis (inclusive parâmetros de deploy e de
criação do superusuário). O `.env` não é versionado (está no `.gitignore`).

Enquanto a aplicação for protótipo, o `.env` da EC2 usa `DJANGO_ALLOWED_HOSTS=*`
para evitar reconfigurar a cada troca de IP. É permissivo; ao ter domínio ou IP
fixo, trocar por lista explícita.

## 6. Estrutura do projeto

```
.
├── config/                     # projeto Django
│   ├── settings.py             # configuracoes (lê variaveis de ambiente; bloco USE_S3/STORAGES)
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
├── midias/                     # app de multimidia (CRUD)
│   ├── templates/midias/       # lista, detalhe, form, confirmar_exclusao
│   ├── migrations/             # 0001_initial (modelo Midia)
│   ├── models.py               # modelo Midia (tipo, dono, arquivo)
│   ├── views.py                # lista, detalhe, criar, editar, excluir
│   ├── forms.py                # MidiaCriarForm, MidiaEditarForm, deteccao de tipo
│   ├── urls.py                 # rotas do app (namespace "midias")
│   ├── admin.py                # MidiaAdmin
│   └── tests.py                # isolamento, validacao de upload, busca
├── docs/                       # documentos de implementacao do Protótipo 2
│   ├── PROTOTIPO_2_MIDIAS.md         # Fase 1: app de midias (CRUD local)
│   ├── PROTOTIPO_2_S3.md             # Fase 2: storage no S3 (AWS + codigo)
│   └── PROTOTIPO_2_S3_DEPLOY_EC2.md  # Fase 2: deploy e validacao do S3 na EC2
├── manage.py
├── requirements.txt            # inclui django-storages, boto3 (S3)
├── .env.example                # modelo de variaveis de ambiente
├── DEPLOY.md                   # runbook de implantacao na EC2
├── README.md
└── CLAUDE.md                   # este briefing
```

## 7. Rotas principais

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

A raiz redireciona para o dashboard; sem login, o `login_required` leva à tela
de entrada. Todas as rotas de `midias` exigem login e filtram por `dono`.

## 8. Convenções de código

* Nomes de modelos, campos e funções em português quando fizer sentido.
* Comentários curtos e só onde agregam; nada de comentário óbvio.
* Seguir o estilo padrão do Django e o PEP 8.
* Views por função com `@login_required`, seguindo o padrão do app `usuarios`.
* Isolamento por usuário sempre via `dono=request.user` nas consultas e
  `get_object_or_404(..., dono=request.user)` nas views de objeto.
* Manter a estilização via Bootstrap (CDN) + `estilo.css`; templates herdam de
  `base.html`, que já traz a navbar e o bloco de mensagens.
* O campo de arquivo continua `FileField`/`ImageField`; a troca de storage
  (disco ↔ S3) é só de configuração, sem mexer em modelo, views ou templates.

## 9. Próximos passos (fora do escopo deste protótipo)

* Banco gerenciado (RDS/PostgreSQL) no lugar do SQLite, em subnet privada com
  acesso liberado apenas a partir do security group da EC2. O driver `psycopg`
  já consta em `requirements.txt`, antecipando essa migração.
* Escalonamento horizontal: Launch Template, ALB e Auto Scaling (o storage no S3
  já deixou a aplicação um passo mais perto de stateless).
* Infraestrutura AWS completa: VPC, grupos de segurança, tabela de rotas.
* HTTPS com certificado e domínio próprio.
* Monitoramento, balanceamento de carga e auto scaling.
