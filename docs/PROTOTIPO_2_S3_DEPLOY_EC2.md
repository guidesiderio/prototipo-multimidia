# Protótipo 2, Fase 2: deploy e validação do S3 na EC2

Documento de execução para o Claude Code. Publica as mudanças da Parte B
(integração S3) na instância EC2 e valida que os binários passam a ir para o
bucket, com URLs assinadas e credenciais pela IAM role. A validação é
programática (Django shell), sem navegador.

## Pré-condições (já atendidas)

- Parte A (console AWS) concluída: bucket `prototipo-multimidia-midias-topicos-engenharia` em `us-east-1`, política `prototipo-s3-midias`, role `prototipo-ec2-s3-role` anexada à instância `prototipo_ec2`.
- Parte B (código) concluída e commitada localmente: `storages` no `INSTALLED_APPS`, bloco `USE_S3`/`STORAGES`, dependências no `requirements.txt`, 5 testes verdes.
- Instância EC2 **running**. IP atual: `98.86.167.130` (muda a cada religada; se tiver mudado, ajuste o host nos comandos).

## Aviso de segurança (ler antes)

- A chave `chave_prototipo.pem` está ignorada pelo Git (`*.pem` no `.gitignore`) e não está no repositório remoto. **Não** versione a chave em hipótese alguma; não rode `git add -f` sobre ela.
- O arquivo `.env` da instância contém segredos (SECRET_KEY). Não imprima o conteúdo dele no log, não o copie para fora da instância e não o commite.
- A chave precisa de permissão restrita para o SSH aceitar usá-la.

---

# Parte 1: publicar o código (local)

No diretório do repositório, na máquina local:

```bash
git status            # confirmar que a Parte B esta commitada
git push origin main  # ajuste o nome do branch se nao for main
```

Se `git status` mostrar mudanças não commitadas da Parte B, commite antes do push.

---

# Parte 2: deploy na instância (via SSH)

Defina o host e a chave uma vez. Ajuste o caminho da chave se você já a moveu
para `~/.ssh`.

```bash
INSTANCIA="ubuntu@98.86.167.130"
CHAVE="chave_prototipo.pem"     # ou ~/.ssh/chave_prototipo.pem se ja moveu

chmod 400 "$CHAVE"              # o SSH recusa a chave se estiver com permissao aberta
```

Conexão de teste (aceita o host key novo de forma não interativa, porque o IP
muda a cada religada):

```bash
ssh -i "$CHAVE" -o StrictHostKeyChecking=accept-new "$INSTANCIA" 'echo conectado; whoami; hostname'
```

Esperado: imprime `conectado`, `ubuntu` e o hostname da instância. Se falhar com
timeout, a instância pode estar parada ou o IP mudou; confirme no console EC2.

## 2.1 Descobrir os caminhos reais a partir do systemd

Em vez de chutar o diretório do projeto, leia do próprio serviço `gunicorn`:

```bash
ssh -i "$CHAVE" "$INSTANCIA" 'systemctl cat gunicorn | grep -E "WorkingDirectory|EnvironmentFile|ExecStart"'
```

Disso saem três coisas:

- `WorkingDirectory=` → diretório do projeto (chame de `PROJ`).
- `EnvironmentFile=` → caminho do `.env` (chame de `ENVFILE`).
- `ExecStart=` → contém o caminho do venv (a parte antes de `/bin/gunicorn`; chame de `VENV`).

Use esses valores reais nos comandos seguintes. O restante deste doc assume,
como exemplo, `PROJ=/home/ubuntu/prototipo-multimidia`, `ENVFILE=$PROJ/.env` e
`VENV=$PROJ/.venv`. **Substitua pelos valores que o comando acima retornou.**

## 2.2 Atualizar código e dependências

```bash
ssh -i "$CHAVE" "$INSTANCIA" 'bash -s' <<'REMOTO'
set -e
PROJ=/home/ubuntu/prototipo-multimidia      # ajustar conforme 2.1
VENV=$PROJ/.venv                            # ajustar conforme 2.1
cd "$PROJ"
git pull --ff-only
"$VENV"/bin/pip install -r requirements.txt
echo "--- pip: pacotes S3 instalados ---"
"$VENV"/bin/pip list | grep -iE "django-storages|boto3|botocore"
REMOTO
```

Esperado: `git pull` traz a Parte B, e o `pip list` mostra `django-storages`,
`boto3` e `botocore`.

## 2.3 Ligar o S3 no `.env` (idempotente)

Remove eventuais linhas antigas dessas três chaves e regrava os valores certos,
preservando o resto do `.env` e a permissão 600:

```bash
ssh -i "$CHAVE" "$INSTANCIA" 'bash -s' <<'REMOTO'
set -e
ENVFILE=/home/ubuntu/prototipo-multimidia/.env   # ajustar conforme 2.1
sed -i '/^USE_S3=/d; /^AWS_STORAGE_BUCKET_NAME=/d; /^AWS_S3_REGION_NAME=/d' "$ENVFILE"
cat >> "$ENVFILE" <<'EOF'
USE_S3=True
AWS_STORAGE_BUCKET_NAME=prototipo-multimidia-midias-topicos-engenharia
AWS_S3_REGION_NAME=us-east-1
EOF
chmod 600 "$ENVFILE"
echo "--- chaves S3 no .env (sem imprimir segredos) ---"
grep -E '^(USE_S3|AWS_STORAGE_BUCKET_NAME|AWS_S3_REGION_NAME)=' "$ENVFILE"
REMOTO
```

O `grep` final mostra só as três chaves novas, não o arquivo inteiro, para não
vazar a SECRET_KEY no log.

## 2.4 Reiniciar o Gunicorn

```bash
ssh -i "$CHAVE" "$INSTANCIA" 'sudo systemctl restart gunicorn && sleep 2 && systemctl is-active gunicorn'
```

Esperado: imprime `active`. Se imprimir `failed`, rode
`ssh -i "$CHAVE" "$INSTANCIA" 'journalctl -u gunicorn -n 30 --no-pager'` e me
reporte a saída.

## 2.5 Validação programática do S3

Este passo prova as quatro permissões da política IAM de uma vez: gravar
(PutObject), checar existência e ler (ListBucket/GetObject), gerar URL assinada e
baixá-la (GET 200), e apagar (DeleteObject). Carrega as variáveis do `.env` antes
de chamar o Django.

```bash
ssh -i "$CHAVE" "$INSTANCIA" 'bash -s' <<'REMOTO'
set -e
PROJ=/home/ubuntu/prototipo-multimidia      # ajustar conforme 2.1
ENVFILE=$PROJ/.env                          # ajustar conforme 2.1
VENV=$PROJ/.venv                            # ajustar conforme 2.1
cd "$PROJ"
set -a; . "$ENVFILE"; set +a
"$VENV"/bin/python manage.py shell -c '
import urllib.request
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

cls = default_storage.__class__
print("BACKEND:", cls.__module__ + "." + cls.__name__)

chave = default_storage.save("midias/_smoketest.txt", ContentFile(b"ok-s3"))
print("SAVED:", chave)
print("EXISTS:", default_storage.exists(chave))

url = default_storage.url(chave)
print("ASSINADA:", "X-Amz-" in url)
print("HTTP:", urllib.request.urlopen(url).getcode())

default_storage.delete(chave)
print("DELETED_OK:", not default_storage.exists(chave))
'
REMOTO
```

### Critérios de sucesso (todos precisam bater)

- `BACKEND:` termina em `storages.backends.s3.S3Storage` (prova que o `USE_S3` pegou).
- `SAVED:` começa com `midias/` (prova PutObject).
- `EXISTS: True` (prova ListBucket/GetObject).
- `ASSINADA: True` (a URL tem parâmetros `X-Amz-`, ou seja, é assinada).
- `HTTP: 200` (o GET pela URL assinada funciona).
- `DELETED_OK: True` (prova DeleteObject e deixa o bucket limpo).

Se o backend ainda aparecer como `FileSystemStorage`, o `.env` não foi recarregado
no shell: confirme que o `set -a; . "$ENVFILE"; set +a` rodou no mesmo bloco e que
`USE_S3=True` está no arquivo.

## 2.6 Conferência de prefixos (opcional, se a AWS CLI existir na instância)

```bash
ssh -i "$CHAVE" "$INSTANCIA" 'command -v aws >/dev/null && aws s3 ls s3://prototipo-multimidia-midias-topicos-engenharia/ --recursive || echo "AWS CLI ausente, pular"'
```

Como o smoke test já apaga o objeto de teste, aqui você só verá prefixos reais
(`midias/`, `perfis/`) depois de uploads de verdade pela aplicação.

---

# Resultado esperado

- `git pull` aplicado, dependências S3 instaladas, `.env` com `USE_S3=True`, Gunicorn `active`.
- Os 6 critérios do passo 2.5 todos verdes.
- A aplicação passa a gravar mídias e fotos de perfil no bucket, fora do disco da instância.

# Rollback rápido

Se algo der errado e for preciso voltar ao disco enquanto se investiga:

```bash
ssh -i "$CHAVE" "$INSTANCIA" 'bash -s' <<'REMOTO'
set -e
ENVFILE=/home/ubuntu/prototipo-multimidia/.env   # ajustar conforme 2.1
sed -i 's/^USE_S3=True/USE_S3=False/' "$ENVFILE"
sudo systemctl restart gunicorn
systemctl is-active gunicorn
REMOTO
```

Volta a usar disco local sem desfazer nenhum código. Os objetos já gravados no
S3 permanecem no bucket.

# Diagnóstico

- `Permission denied (publickey)`: a chave não é a da instância, ou está sem `chmod 400`, ou o usuário não é `ubuntu`.
- `AccessDenied` no `SAVED`/`EXISTS`: a role `prototipo-ec2-s3-role` não está anexada à instância, ou a política não cobre o ARN do bucket. Reveja a Parte A (passos A.2 e A.4 do doc anterior).
- `BACKEND: ...FileSystemStorage`: `USE_S3` não chegou ao processo; confira o `.env` e o carregamento das variáveis no passo 2.5.
- `NoSuchBucket` ou `EndpointConnectionError`: nome do bucket errado no `.env`, ou região diferente de `us-east-1`.
- Gunicorn `failed` após restart: ver `journalctl -u gunicorn -n 30 --no-pager`; em geral é dependência não instalada no venv (refazer 2.2) ou erro de sintaxe no `.env`.

# Próxima fase (não executar agora)

Migrar o banco do SQLite para RDS/PostgreSQL, com o RDS em subnet privada e
acesso liberado apenas a partir do security group da EC2.
