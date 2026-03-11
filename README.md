# OpenTelemetry Lab: Flask + Celery + Dynatrace

Este projeto demonstra como instrumentar uma aplicação Flask + Celery com OpenTelemetry para enviar traces, métricas e logs para o Dynatrace (ou Jaeger para testes locais).

## 🏗️ Arquitetura

```
┌─────────────┐     ┌─────────────┐     ┌────────────────┐
│  Flask API  │────▶│  RabbitMQ   │────▶│  Celery Worker │
│  :8000      │     │  :5672      │     │                │
└──────┬──────┘     └─────────────┘     └───────┬────────┘
       │                                        │
       │            ┌─────────────┐             │
       └───────────▶│    OTel     │◀────────────┘
                    │  Collector  │
                    │  :4318      │
                    └──────┬──────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
       ┌─────────────┐          ┌─────────────┐
       │   Jaeger    │          │  Dynatrace  │
       │   :16686    │          │  (futuro)   │
       └─────────────┘          └─────────────┘
```

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

## 📁 Estrutura do Projeto

```
opentelemetry_lab/
├── docker-compose.yaml          # Orquestração dos containers
├── Dockerfile                   # Build da aplicação Python
├── requirements.txt             # Dependências Python
├── otel-collector-config.yaml   # Configuração do OTel Collector
├── .env.example                 # Template de variáveis de ambiente
├── README.md                    # Este arquivo
└── app/
    ├── __init__.py
    ├── main.py                  # Entrypoint Flask
    ├── api.py                   # Endpoints REST
    ├── celery_app.py            # Configuração Celery
    ├── tasks.py                 # Tasks Celery
    └── tracing.py               # Setup OpenTelemetry
```

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

### 2. Configurar o Collector

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

### 3. Reiniciar o ambiente

```bash
docker-compose down
docker-compose up --build
```

### 4. Verificar no Dynatrace

1. Acesse seu ambiente Dynatrace
2. Vá em **Services** → procure por `flask-api` ou `celery-worker`
3. Ou vá em **Distributed traces** para ver os traces

## 🛠️ Desenvolvimento Local

### Sem Docker

```bash
# Instalar dependências
pip install -r requirements.txt

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
export OTEL_SERVICE_NAME=flask-api

# Iniciar Celery Worker (em um terminal)
celery -A app.celery_app worker --loglevel=info

# Iniciar Flask (em outro terminal)
python -m flask --app app.main run --port 8000
```

## 📊 O que é rastreado

### Traces automáticos
- ✅ Requisições HTTP (Flask)
- ✅ Execução de tasks Celery
- ✅ Chamadas HTTP externas (requests)
- ✅ Contexto propagado entre Flask → Celery

### Spans manuais (exemplos em `tasks.py`)
- ✅ Processamento por etapas (slow_task)
- ✅ Processamento em batch (process_data)
- ✅ Atributos customizados
- ✅ Eventos de span

### Logs
- ✅ Correlação automática com trace_id/span_id
- ✅ Exportação para OTel Collector
- ✅ Formato estruturado

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

## 📚 Referências

- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)
- [Celery Documentation](https://docs.celeryq.dev/)
- [Dynatrace OpenTelemetry Integration](https://www.dynatrace.com/support/help/extend-dynatrace/opentelemetry)
- [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/)

## 📝 Licença

MIT
