# Aplicação Web Multimídia

Aplicação web para gerenciamento de objetos multimídia (imagens, áudios e
vídeos), desenvolvida na disciplina Tópicos em Engenharia de Software
(Computação em Nuvem), UFPI, turma 2026.1, Prof. Armando Soares Sousa.

## Status

1º protótipo (Avaliação 2). Esta entrega cobre a fundação da aplicação:
autenticação, dashboard e gerenciamento de perfil de usuário. O upload de
multimídia e a implantação completa na AWS entram nos protótipos seguintes.

## Funcionalidades desta entrega

1. Registro de novos usuários.
2. Login e logout.
3. Dashboard exibido após autenticação.
4. Edição de perfil (nome completo, email, descrição e foto) e alteração de senha.

Cada usuário possui: nome completo, username, password, email, foto de perfil,
descrição e data de criação.

## Stack

- Python e Django (versão 5 ou superior)
- SQLite como banco de dados (será substituído por PostgreSQL/RDS em protótipo posterior)
- Templates do Django renderizados no servidor
- Ambiente isolado com venv

## Pré-requisitos

- Python 3.10 ou superior
- Git

## Como executar localmente

```bash
# clonar o repositorio
git clone <url-do-repositorio>
cd <pasta-do-projeto>

# criar e ativar o ambiente virtual
python3 -m venv .venv
source .venv/bin/activate

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

## Rotas principais

| Rota              | Descrição                       |
| ----------------- | ------------------------------- |
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
├── config/            # configuracoes e rotas do projeto Django
├── usuarios/          # app de autenticacao e perfil
│   ├── templates/usuarios/
│   ├── models.py
│   ├── views.py
│   ├── forms.py
│   ├── urls.py
│   └── admin.py
├── manage.py
├── requirements.txt
└── README.md
```

## Equipe

| Nome                         | Matrícula   | Colaboração |
| ---------------------------- | ----------- | ----------- |
| Guilherme Oliveira Desidério | 20219036892 |             |
|                              |             |             |
|                              |             |             |
|                              |             |             |
|                              |             |             |

## Próximos passos

- Implantação na AWS: VPC, instância EC2, grupos de segurança, tabela de rotas e IP público.
- Upload e gerenciamento de arquivos multimídia (S3).
- Banco gerenciado (RDS/PostgreSQL).
- Monitoramento, balanceamento de carga e auto scaling.
