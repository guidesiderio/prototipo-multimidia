# Protótipo 2, Fase 2: armazenamento de binários no S3

Documento de implementação. Move os arquivos enviados (mídias e fotos de perfil)
do disco da instância para um bucket S3 privado, com URLs assinadas e
credenciais via IAM role anexada à EC2. Atende o requisito da Avaliação 3 de
salvar e recuperar objetos binários no AWS S3, e começa a deixar a aplicação
stateless (pré-requisito do Auto Scaling).

O documento tem duas partes:

- **Parte A, AWS no console**: passos manuais (bucket, política IAM, role). Executados por você, não pelo Claude Code.
- **Parte B, código**: alterações no projeto. Executadas pelo Claude Code.

## Decisões fixadas

- Bucket **privado**: Block Public Access ON, ACLs desabilitadas (bucket owner enforced).
- Acesso aos arquivos por **URLs assinadas** (querystring auth), validade de 1 hora.
- Credenciais em produção pela **IAM role** anexada à EC2, sem chaves no `.env`. O boto3 lê a role automaticamente.
- **Toggle `USE_S3`**, desligado por padrão. Local usa disco; a EC2 usa S3. Nenhuma credencial AWS na máquina local.
- `STORAGES["default"]` vira S3, então tanto `midias.arquivo` quanto `usuarios.foto_perfil` passam a gravar no bucket. Os estáticos continuam no disco servidos pelo Nginx.
- Bucket na região `us-east-1`, mesma da VPC do Protótipo 1.

---

# Parte A: AWS no console (manual)

## A.1 Criar o bucket

1. S3, Create bucket.
2. Nome único globalmente, por exemplo `prototipo-multimidia-midias-<seu-sufixo>`. Anote o nome exato.
3. Região: `us-east-1`.
4. Object Ownership: **ACLs disabled (bucket owner enforced)**.
5. Block Public Access: **manter tudo marcado (ON)**.
6. Default encryption: SSE-S3 (Amazon S3 managed keys).
7. Create bucket.

Não precisa de bucket policy. O acesso vem da IAM role, não de regra pública.

## A.2 Criar a política IAM (menor privilégio)

IAM, Policies, Create policy, aba JSON. Troque `NOME-DO-BUCKET` pelo nome real
nos dois lugares.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ObjetosDoBucket",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::NOME-DO-BUCKET/*"
    },
    {
      "Sid": "ListarBucket",
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::NOME-DO-BUCKET"
    }
  ]
}
```

Nomeie a política, por exemplo `prototipo-s3-midias`, e crie.

A distinção dos dois blocos: ações sobre objetos usam o ARN com `/*`; `ListBucket`
é uma ação sobre o bucket em si, então usa o ARN sem `/*`.

## A.3 Criar a role para a EC2

1. IAM, Roles, Create role.
2. Trusted entity type: AWS service. Use case: **EC2**.
3. Anexe a política `prototipo-s3-midias`.
4. Nomeie, por exemplo `prototipo-ec2-s3-role`, e crie.

## A.4 Anexar a role à instância

1. EC2, Instances, selecione `prototipo_ec2`.
2. Actions, Security, Modify IAM role.
3. Selecione `prototipo-ec2-s3-role`, Update IAM role.

A role passa a valer na hora, sem reiniciar a instância. Quando o Launch Template
do Auto Scaling for criado na fase de escalonamento, ele vai referenciar esse
mesmo instance profile, então toda instância nova nasce com o acesso ao S3.

---

# Parte B: código (Claude Code executa)

## B.1 Dependências

Instale e congele as versões no `requirements.txt`:

```bash
pip install django-storages==1.14.6 boto3
pip freeze | grep -iE "django-storages|boto3|botocore|jmespath|s3transfer" >> requirements.txt
```

Depois ordene/limpe o `requirements.txt` se houver duplicidade, mantendo uma
linha por pacote com versão fixada.

## B.2 `config/settings.py`

### B.2.1 Registrar o app `storages`

ANTES:
```python
    'usuarios',
    'midias',
]
```
DEPOIS:
```python
    'usuarios',
    'midias',
    'storages',
]
```

### B.2.2 Bloco de storage

Localize o trecho atual de media/estáticos:

ANTES:
```python
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"

STATIC_ROOT = BASE_DIR / "staticfiles"
```
DEPOIS:
```python
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"

STATIC_ROOT = BASE_DIR / "staticfiles"

# Armazenamento de binarios no S3 (ligado por variavel de ambiente).
# Local: USE_S3 ausente ou diferente de "True", usa disco (padrao do Django).
# Producao (EC2): USE_S3=True, usa o bucket S3 via IAM role anexada a instancia.
USE_S3 = os.environ.get("USE_S3", "False") == "True"

if USE_S3:
    AWS_STORAGE_BUCKET_NAME = os.environ.get("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = os.environ.get("AWS_S3_REGION_NAME", "us-east-1")
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "bucket_name": AWS_STORAGE_BUCKET_NAME,
                "region_name": AWS_S3_REGION_NAME,
                "querystring_auth": True,      # gera URLs assinadas
                "querystring_expire": 3600,    # validade da URL em segundos (1 hora)
                "default_acl": None,           # bucket com ACLs desabilitadas
                "file_overwrite": False,       # nao sobrescreve arquivo de mesmo nome
                "signature_version": "s3v4",
            },
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
```

Pontos da configuração:

- Não há `AWS_ACCESS_KEY_ID` nem `AWS_SECRET_ACCESS_KEY`. O boto3 obtém as credenciais da IAM role da instância.
- Só o storage `default` (media) aponta para o S3. O `staticfiles` continua local, servido pelo Nginx.
- Como `default` é global, qualquer `FileField`/`ImageField` do projeto passa a usar o S3, incluindo o `foto_perfil` do `Usuario`.
- Quando `USE_S3` é falso, o setting `STORAGES` não é definido e o Django usa os padrões (disco), então o desenvolvimento local e os testes não tocam no S3.

## B.3 `.env.example`

Acrescente as variáveis novas (sem valores reais):

```bash
# S3 (somente em producao; deixe USE_S3=False ou ausente em desenvolvimento)
USE_S3=False
AWS_STORAGE_BUCKET_NAME=
AWS_S3_REGION_NAME=us-east-1
```

## B.4 Nada muda no modelo, nas views nem nos templates

O campo `arquivo` continua `FileField(upload_to="midias/")`. As URLs nos
templates (`{{ midia.arquivo.url }}`) passam a vir assinadas pelo storage do S3
de forma transparente. As views e os testes ficam como estão.

---

# Validação

## Local (USE_S3 desligado)

```bash
python manage.py test midias
python manage.py runserver
```

Os 5 testes do app `midias` continuam passando, e o upload local grava em
`media/midias/` como antes. Confirma que a mudança não quebrou o fluxo de disco.

## Produção (na EC2, USE_S3 ligado)

1. No `.env` da instância, defina (e reinicie o Gunicorn depois):
   ```bash
   USE_S3=True
   AWS_STORAGE_BUCKET_NAME=NOME-DO-BUCKET
   AWS_S3_REGION_NAME=us-east-1
   ```
   ```bash
   sudo systemctl restart gunicorn
   ```
2. Instale as dependências novas se ainda não estiverem na instância:
   ```bash
   source .venv/bin/activate && pip install -r requirements.txt
   ```
3. Pelo navegador, crie uma mídia (imagem) e confirme:
   - O detalhe renderiza a imagem (a URL no HTML é assinada, com parâmetros `X-Amz-...`).
   - O objeto aparece no bucket, sob o prefixo `midias/`.
4. Edite a foto de perfil e confirme que o objeto cai sob o prefixo `perfis/` no mesmo bucket.
5. Opcional, prova do stateless: pare e religue a instância (o IP muda) e confirme que as mídias continuam acessíveis, porque o binário está no S3, não no disco.

## Diagnóstico rápido se algo falhar

- `AccessDenied` na gravação ou leitura: a role não está anexada à instância, ou a política não cobre o ARN do bucket. Reveja A.2 e A.4.
- Erro de credencial/assinatura: confirme `AWS_S3_REGION_NAME=us-east-1` e que não há chaves antigas no ambiente atrapalhando a role.
- `NoSuchBucket`: nome do bucket no `.env` diferente do criado.

---

# Migração dos arquivos já existentes

Arquivos que foram enviados antes (fotos de perfil e mídias de teste no disco da
instância) não migram sozinhos para o S3; as linhas no banco apontam para chaves
que ainda não existem no bucket. Para o protótipo, duas opções:

- Reenviar os poucos arquivos pela interface depois de ligar o `USE_S3`.
- Copiar o conteúdo preservando os caminhos, uma única vez, na instância:
  ```bash
  aws s3 cp media/ s3://NOME-DO-BUCKET/ --recursive
  ```
  (requer AWS CLI na instância; a role já dá a permissão de escrita.)

---

# Estado após esta fase

- Binários no S3, fora do disco da instância. A foto de perfil também deixa de ser presa ao disco.
- Aplicação um passo mais perto de stateless. Falta tirar o banco do SQLite local, o que é a próxima fase (RDS/PostgreSQL).
- Estáticos seguem no disco, servidos pelo Nginx, compatíveis com múltiplas instâncias idênticas.

## Próxima fase (não implementar agora)

Migrar o banco do SQLite para RDS/PostgreSQL, com o RDS em subnet privada e
acesso liberado apenas a partir do security group da EC2. O `psycopg` já está no
`requirements.txt`; a troca é de configuração do `DATABASES` por variável de
ambiente, sem alterar modelos.
