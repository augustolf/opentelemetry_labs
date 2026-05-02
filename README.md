# OpenTelemetry Lab: Flask + Celery + Dynatrace

Este projeto demonstra como instrumentar **automaticamente** uma aplicação Flask + Celery com OpenTelemetry usando `opentelemetry-instrument`, enviando traces, métricas e logs para o Dynatrace (ou Jaeger para testes locais).

## 🏗️ Arquitetura

```
┌─────────────┐     ┌─────────────┐     ┌────────────────┐
│  Flask API  │────▶│  RabbitMQ   │────▶│  Celery Worker │
│  :8000      │     │  :5672      │     │                │
└──────┬──────┘     └─────────────┘     └───────┬────────┘
       │                                        │
       │  opentelemetry-instrument               │  opentelemetry-instrument
       │  (auto-instrumentação)                  │  (auto-instrumentação)
       │            ┌─────────────┐             │
       └───────────▶│    OTel     │◀────────────┘
                    │  Collector  │
                    │  :4317/4318 │
                    └──────┬──────┘
                           │
         ┌─────────────────┼──────────────────┐
         ▼                 ▼                  ▼
  ┌─────────────┐  ┌─────────────┐   ┌─────────────┐
  │   Jaeger    │  │  Prometheus │   │  Dynatrace  │
  │   :16686    │  │  :9090      │   │  (opcional) │
  └─────────────┘  └──────┬──────┘   └─────────────┘
                          │
                   ┌──────▼──────┐
                   │   Grafana   │
                   │   :3000     │
                   └─────────────┘
```

## ⚙️ Como funciona a auto-instrumentação

Este projeto usa o agente `opentelemetry-instrument` ([documentação Dynatrace](https://docs.dynatrace.com/docs/ingest-from/opentelemetry/walkthroughs/python/python-auto)) para instrumentar a aplicação **sem código manual de SDK**.

### O que o agente faz automaticamente:
- Cria o `TracerProvider`, `MeterProvider` e `LoggerProvider`
- Configura exporters OTLP baseados nas variáveis `OTEL_*`
- Detecta e instrumenta bibliotecas: Flask, Celery, requests, logging, etc.
- Propaga contexto (W3C TraceContext) entre serviços

### Como é usado:
```bash
# Em vez de:
gunicorn app.main:app
celery -A app.celery_app worker

# Usamos:
opentelemetry-instrument gunicorn app.main:app
opentelemetry-instrument celery -A app.celery_app worker
```

### Dependências mínimas:
```
opentelemetry-distro         # Inclui SDK + distro
opentelemetry-exporter-otlp  # Exporters OTLP (HTTP + gRPC)
```

O comando `opentelemetry-bootstrap -a install` (executado no Dockerfile) detecta as bibliotecas instaladas e instala automaticamente as instrumentações aplicáveis.

## 🚀 Quick Start

### 1. Subir o ambiente

```bash
docker-compose up --build
```

### 2. Verificar os serviços

| Serviço | URL | Descrição |
|---------|-----|-----------|
| Flask API | http://localhost:8000 | API REST |
| Jaeger UI | http://localhost:16686 | Visualização de traces |
| Grafana | http://localhost:3000 | Dashboards de métricas |
| Prometheus | http://localhost:9090 | Query de métricas |
| RabbitMQ | http://localhost:15672 | Management UI (guest/guest) |
| Flower | http://localhost:5555 | Monitor de tasks Celery |

### 3. Testar a API

```bash
# Health check
curl http://localhost:8000/health

# Executar task síncrona (aguarda resultado)
curl http://localhost:8000/api/task/sync

# Disparar task de adição
curl -X POST http://localhost:8000/api/task/add \
  -H "Content-Type: application/json" \
  -d '{"x": 10, "y": 20}'

# Disparar task lenta (5 segundos)
curl -X POST http://localhost:8000/api/task/slow \
  -H "Content-Type: application/json" \
  -d '{"duration": 5}'

# Buscar URL externa
curl -X POST http://localhost:8000/api/task/fetch \
  -H "Content-Type: application/json" \
  -d '{"url": "https://httpbin.org/json"}'

# Verificar status de uma task
curl http://localhost:8000/api/task/{task_id}/status

# Aguardar resultado de uma task
curl http://localhost:8000/api/task/{task_id}/result?timeout=30
```

### 4. Visualizar traces no Jaeger

1. Abra http://localhost:16686
2. Selecione o serviço `flask-api` ou `celery-worker`
3. Clique em "Find Traces"
4. Clique em um trace para ver os detalhes

### 5. Visualizar métricas no Grafana

1. Abra http://localhost:3000
2. Vá em **Connections → Data Sources → Add → Prometheus**
3. URL: `http://prometheus:9090` → clique em **Save & Test**
4. Vá em **Dashboards → New → Import**
5. Use o ID `15983` para importar o dashboard oficial do OpenTelemetry Collector

## 📁 Estrutura do Projeto

```
opentelemetry_lab/
├── docker-compose.yaml          # Orquestração dos containers
├── Dockerfile                   # Build + opentelemetry-bootstrap
├── requirements.txt             # Dependências (opentelemetry-distro + exporter)
├── otel-collector-config.yaml   # Configuração do OTel Collector
├── prometheus.yml               # Configuração do Prometheus (scraping do Collector)
├── .env.example                 # Template de variáveis de ambiente
├── README.md                    # Este arquivo
└── app/
    ├── __init__.py
    ├── main.py                  # Entrypoint Flask (sem código OTel)
    ├── api.py                   # Endpoints REST
    ├── celery_app.py            # Configuração Celery (sem código OTel)
    ├── tasks.py                 # Tasks Celery (com spans manuais opcionais)
    └── tracing.py               # Helpers: get_tracer() e get_meter()
```

> **Nota:** O código da aplicação (`main.py`, `celery_app.py`) não contém nenhuma inicialização do SDK OpenTelemetry. Toda instrumentação é feita pelo agente `opentelemetry-instrument` via variáveis de ambiente.

## 🔧 Endpoints da API

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/` | Informações da API |
| GET | `/health` | Health check |
| GET | `/api/health` | Health check da API |
| POST | `/api/task/add` | Task de adição `{x, y}` |
| POST | `/api/task/multiply` | Task de multiplicação `{x, y}` |
| POST | `/api/task/slow` | Task lenta `{duration}` |
| POST | `/api/task/fetch` | Buscar URL `{url}` |
| POST | `/api/task/process` | Processar dados `{data: [...]}` |
| POST | `/api/task/chain` | Executar chain de tasks `{value}` |
| POST | `/api/task/parallel` | Executar tasks em paralelo `{values: [...]}` |
| POST | `/api/task/error` | Task com erro `{should_fail}` |
| GET | `/api/task/sync` | Task síncrona (aguarda resultado) |
| GET | `/api/task/<id>/status` | Status de uma task |
| GET | `/api/task/<id>/result` | Resultado de uma task |

## 🔧 Variáveis de ambiente OpenTelemetry

Variáveis usadas pelo agente `opentelemetry-instrument` (configuradas no `docker-compose.yaml`):

| Variável | Valor | Descrição |
|----------|-------|-----------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://otel-collector:4318` | Endpoint do Collector |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | `http/protobuf` | Protocolo de exportação |
| `OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE` | `delta` | Temporalidade de métricas (requerido pelo Dynatrace) |
| `OTEL_SERVICE_NAME` | `flask-api` / `celery-worker` | Nome do serviço |
| `OTEL_RESOURCE_ATTRIBUTES` | `deployment.environment=development,...` | Atributos do recurso |
| `OTEL_PYTHON_LOG_CORRELATION` | `true` | Adiciona trace_id/span_id nos logs |
| `OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED` | `true` | Exporta logs automáticos via OTLP |

## 🔗 Configurar Dynatrace

### 1. Obter credenciais do Dynatrace

1. Acesse seu ambiente Dynatrace
2. Vá em **Settings → Access Tokens → Generate new token**
3. Dê um nome ao token (ex: `otel-ingest`)
4. Selecione os escopos:
   - `openTelemetryTrace.ingest`
   - `metrics.ingest`
   - `logs.ingest`
5. Clique em **Generate** e copie o token

### 2. Opção A — Via Collector (recomendado)

Edite o arquivo `otel-collector-config.yaml` e descomente o exporter do Dynatrace:

```yaml
exporters:
  # Descomente e configure:
  otlphttp/dynatrace:
    endpoint: https://{ENVIRONMENT_ID}.live.dynatrace.com/api/v2/otlp
    headers:
      Authorization: "Api-Token {SEU_TOKEN_AQUI}"
    compression: gzip

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, resource, batch]
      exporters: [debug, otlp/jaeger, otlphttp/dynatrace]  # Adicione otlphttp/dynatrace

    metrics:
      receivers: [otlp]
      processors: [memory_limiter, resource, batch]
      exporters: [debug, otlphttp/dynatrace]  # Adicione otlphttp/dynatrace

    logs:
      receivers: [otlp]
      processors: [memory_limiter, resource, batch]
      exporters: [debug, otlphttp/dynatrace]  # Adicione otlphttp/dynatrace
```

**Vantagens:** Token em um único lugar, Jaeger + Dynatrace ao mesmo tempo, melhor resiliência.

### 2. Opção B — Direto ao Dynatrace (sem Collector)

Altere as variáveis de ambiente nos serviços `flask-api` e `celery-worker` no `docker-compose.yaml`:

```yaml
environment:
  OTEL_EXPORTER_OTLP_ENDPOINT: https://{ENVIRONMENT_ID}.live.dynatrace.com/api/v2/otlp
  OTEL_EXPORTER_OTLP_HEADERS: "Authorization=Api-Token%20{SEU_TOKEN_AQUI}"
  OTEL_EXPORTER_OTLP_PROTOCOL: http/protobuf
  OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE: delta
```

> **Nota:** O espaço no header é codificado como `%20` (convenção W3C Baggage).

**Vantagens:** Menos infraestrutura, setup mais simples para cenários serverless.

### 3. Reiniciar o ambiente

```bash
docker-compose down
docker-compose up --build
```

### 4. Verificar no Dynatrace

1. Acesse seu ambiente Dynatrace
2. Vá em **Distributed Traces Classic** → aba **Ingested traces**
3. Ou vá em **Logs & Events Classic** para ver os logs correlacionados
4. Vá em **Metrics** para métricas do runtime

## 🛠️ Desenvolvimento Local

### Sem Docker

```bash
# Instalar dependências e instrumentações automáticas
pip install -r requirements.txt
opentelemetry-bootstrap -a install

# Iniciar RabbitMQ (ou use Docker)
docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3.12-management-alpine

# Iniciar OTel Collector (ou use Docker)
docker run -d --name otel-collector -p 4317:4317 -p 4318:4318 \
  -v $(pwd)/otel-collector-config.yaml:/etc/otel-collector-config.yaml \
  otel/opentelemetry-collector-contrib:0.96.0 \
  --config=/etc/otel-collector-config.yaml

# Definir variáveis de ambiente
export CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
export OTEL_SERVICE_NAME=flask-api

# Iniciar Celery Worker com auto-instrumentação (em um terminal)
OTEL_SERVICE_NAME=celery-worker opentelemetry-instrument celery -A app.celery_app worker --loglevel=info

# Iniciar Flask com auto-instrumentação (em outro terminal)
OTEL_SERVICE_NAME=flask-api opentelemetry-instrument gunicorn --bind 0.0.0.0:8000 app.main:app
```

## 📊 O que é rastreado

### Traces automáticos (via `opentelemetry-instrument`)
- ✅ Requisições HTTP (Flask) — detectado automaticamente
- ✅ Execução de tasks Celery — detectado automaticamente
- ✅ Chamadas HTTP externas (requests) — detectado automaticamente
- ✅ Contexto propagado entre Flask → Celery (W3C TraceContext)
- ✅ Logging correlacionado — trace_id/span_id injetados nos logs

### Spans manuais (exemplos em `tasks.py`)
- ✅ Processamento por etapas (slow_task) — via `get_tracer()`
- ✅ Processamento em batch (process_data)
- ✅ Atributos customizados
- ✅ Eventos de span

> Os spans manuais funcionam normalmente com `opentelemetry-instrument` — o agente configura o `TracerProvider` global, e `trace.get_tracer()` retorna um tracer funcional.

## 🐛 Troubleshooting

### Traces não aparecem no Jaeger
1. Verifique se o OTel Collector está rodando: `docker-compose logs otel-collector`
2. Verifique a conectividade: `curl http://localhost:4318/v1/traces`
3. Verifique os logs do Flask: `docker-compose logs flask-api`

### Tasks não executam
1. Verifique se o RabbitMQ está pronto: `docker-compose logs rabbitmq`
2. Verifique o Celery Worker: `docker-compose logs celery-worker`
3. Acesse o Flower para monitorar: http://localhost:5555

### Erros de conexão
1. Aguarde todos os serviços subirem (RabbitMQ pode demorar)
2. Use `docker-compose up -d` e `docker-compose logs -f` para acompanhar

### Auto-instrumentação não funciona
1. Verifique se `opentelemetry-bootstrap -a install` rodou no build do Docker
2. Confirme que o command usa `opentelemetry-instrument` como prefixo
3. Verifique as variáveis `OTEL_*` com `docker-compose exec flask-api env | grep OTEL`

## 📚 Referências

- [OpenTelemetry Python Auto-Instrumentation](https://opentelemetry.io/docs/languages/python/automatic/)
- [Dynatrace: Auto-instrumentar Python com OpenTelemetry](https://docs.dynatrace.com/docs/ingest-from/opentelemetry/walkthroughs/python/python-auto)
- [Celery Documentation](https://docs.celeryq.dev/)
- [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/)
- [Dynatrace OTLP API Endpoints](https://docs.dynatrace.com/docs/ingest-from/opentelemetry/otlp-api)

## 📝 Licença

MIT
