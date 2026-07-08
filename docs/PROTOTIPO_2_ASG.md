# Fase 4: Escalonamento Horizontal com ALB e Auto Scaling

## Objetivo

Após a migração do banco para o RDS e dos arquivos para o S3, a aplicação não possui mais estado local. Isso permite que múltiplas instâncias EC2 executem a aplicação simultaneamente atrás de um balanceador de carga.

Nesta fase serão criados:

* Segunda subnet pública em outra Availability Zone.
* Application Load Balancer (ALB).
* Launch Template.
* Auto Scaling Group (ASG).

---

# 1. Situação Atual

A infraestrutura já possui:

* VPC `prototipo_vpc`
* Subnet pública `10.0.1.0/24`
* Subnets privadas:

  * `10.0.2.0/24`
  * `10.0.3.0/24`
* Banco PostgreSQL no RDS
* Bucket S3 para armazenamento das mídias
* Aplicação Django executando em EC2 com Gunicorn e Nginx
* IAM Role para acesso ao S3
* Configuração por variáveis de ambiente (`.env`)

Como os dados estão armazenados no RDS e os arquivos no S3, qualquer instância EC2 pode atender requisições sem depender de dados locais.

---

# 2. Criar a Segunda Subnet Pública

A AWS exige pelo menos duas Availability Zones para o Application Load Balancer.

Acesse:

```text
VPC → Subnets → Create subnet
```

Selecione a VPC:

```text
prototipo_vpc
```

Crie a subnet:

| Campo             | Valor            |
| ----------------- | ---------------- |
| Name              | subnet_publica_b |
| Availability Zone | us-east-1b       |
| CIDR              | 10.0.4.0/24      |

Resultado esperado:

| Subnet           | AZ         |
| ---------------- | ---------- |
| subnet_publica | us-east-1a |
| subnet_publica_b | us-east-1b |

---

# 3. Associar à Route Table Pública

Acesse:

```text
VPC → Route Tables
```

Selecione a route table pública existente.

Ela deve possuir:

| Destino     | Alvo             |
| ----------- | ---------------- |
| 10.0.0.0/16 | local            |
| 0.0.0.0/0   | Internet Gateway |

Na aba **Subnet Associations**, associe:

* subnet_publica
* subnet_publica_b

---

# 4. Criar o Security Group do ALB

Acesse:

```text
EC2 → Security Groups → Create Security Group
```

Nome:

```text
sg_alb
```

## Inbound Rules

| Tipo | Porta | Origem    |
| ---- | ----- | --------- |
| HTTP | 80    | 0.0.0.0/0 |

## Outbound Rules

| Tipo        | Destino   |
| ----------- | --------- |
| All Traffic | 0.0.0.0/0 |

---

# 5. Ajustar o Security Group das Instâncias

O grupo `sg_web` não deve mais aceitar HTTP da Internet.

## Inbound Rules

| Tipo | Porta | Origem |
| ---- | ----- | ------ |
| HTTP | 80    | sg_alb |
| SSH  | 22    | Seu IP |

Dessa forma apenas o ALB pode acessar as instâncias.

---

# 6. Criar uma AMI da Instância Atual

A instância já está configurada com:

* Django
* Gunicorn
* Nginx
* IAM Role
* Conexão com o RDS
* Conexão com o S3
* Arquivo `.env`

Acesse:

```text
EC2 → Instances
```

Selecione a instância.

```text
Actions → Image and templates → Create Image
```

Nome:

```text
ami-prototipo-v1
```

Aguarde o status:

```text
Available
```

---

# 7. Criar o Launch Template

Acesse:

```text
EC2 → Launch Templates → Create Launch Template
```

## Nome

```text
lt-prototipo
```

## AMI

Selecione:

```text
ami-prototipo-v1
```

## Tipo da Instância

```text
t3.micro
```

## Key Pair

Selecione a chave SSH utilizada no projeto.

## Security Group

```text
sg_web
```

## IAM Role

Selecione a role utilizada para acesso ao bucket S3.

Exemplo:

```text
ec2-s3-role
```



# 8. Criar o Target Group

Acesse:

```text
EC2 → Target Groups → Create Target Group
```

## Configuração

| Campo       | Valor         |
| ----------- | ------------- |
| Target Type | Instances     |
| Protocol    | HTTP          |
| Port        | 80            |
| VPC         | prototipo_vpc |

Nome:

```text
tg-prototipo
```

## Health Check

```text
/
```

ou

```text
/login/
```

---

# 9. Criar o Application Load Balancer

Acesse:

```text
EC2 → Load Balancers → Create Load Balancer
```

Escolha:

```text
Application Load Balancer
```

## Nome

```text
alb-prototipo
```

## Scheme

```text
Internet-facing
```

## IP Type

```text
IPv4
```

## Network Mapping

Selecione:

* subnet_publica
* subnet_publica_b

## Security Group

```text
sg_alb
```

## Listener

```text
HTTP : 80
```

## Target Group

```text
tg-prototipo
```

---

# 10. Criar o Auto Scaling Group

Acesse:

```text
EC2 → Auto Scaling Groups → Create Auto Scaling Group
```

## Nome

```text
asg-prototipo
```

## Launch Template

```text
lt-prototipo
```

## VPC

```text
prototipo_vpc
```

## Subnets

Selecione:

* subnet_publica
* subnet_publica_b

## Load Balancer

Escolha:

```text
Attach to existing load balancer
```

e selecione:

```text
tg-prototipo
```

---

# 11. Definir a Capacidade

| Configuração     | Valor |
| ---------------- | ----- |
| Desired Capacity | 2     |
| Minimum Capacity | 2     |
| Maximum Capacity | 6     |

Resultado:

* Sempre existirão duas instâncias em execução.
* O grupo poderá crescer até quatro instâncias.

---

# 12. Configurar Escalonamento Automático

Selecione:

```text
Target Tracking Scaling Policy
```

Métrica:

```text
Average CPU Utilization
```

Meta:

```text
90%
```

Comportamento:

* CPU acima de 90% → cria novas instâncias.
* CPU abaixo de 90% → remove instâncias excedentes.

Exemplo:

```text
2 → 3 → 4 → 5 → 6 instâncias
```

e depois:

```text
6 → 5 → 4 → 3 → 2 instâncias
```

---


## Resultado Final

Após esta fase:

* Aplicação distribuída entre múltiplas instâncias.
* Balanceamento de carga realizado pelo ALB.
* Escalonamento automático conforme a demanda.
* Banco centralizado no RDS.
* Arquivos armazenados no S3.
* Nenhum estado persistente armazenado localmente na EC2.
* Alta disponibilidade entre duas Availability Zones.
