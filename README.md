# Risco de Credito Amazonas MVP

MVP local-first para nowcasting mensal de inadimplencia com foco no Amazonas. O projeto reune ingestao de dados, processamento, modelagem, API em FastAPI e dashboard em Streamlit para validar fontes reais, gerar previsoes e acompanhar a qualidade dos dados.

## O que o projeto entrega

- Pipeline de ingestao e consolidacao de fontes economicas.
- Geracao de features para nowcasting de inadimplencia.
- Treino, avaliacao e registro de previsoes.
- API em FastAPI para operacao e validacao.
- Dashboard em Streamlit para acompanhamento local.

## Estrutura

- `src/ingestion`: clientes de ingestao.
- `src/processing`: alinhamento, qualidade e features.
- `src/modeling`: treino, avaliacao e predicao.
- `src/api`: API FastAPI.
- `src/app`: dashboard Streamlit.
- `src/jobs`: orquestracao do pipeline.

## Executar localmente

```bash
cd project
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m unittest discover -s tests
uvicorn src.api.main:app --reload
```

## Docker Compose

```bash
cd project/infra
docker compose up --build
```

Servicos:
- API: `http://localhost:8000`
- Dashboard: `http://localhost:8501`

## Endpoints uteis

- `GET /pipeline/validate-sources`: valida fontes reais sem treino.
- `POST /pipeline/run-real-acceptance`: roda o checklist de aceite com fontes reais.
- `GET /pipeline/data-quality`: gera um resumo basico de qualidade de dados.

Alternativa via CLI:

```bash
python -m src.jobs.run_real_acceptance
```

## Persistencia

- Banco SQLite local: `data/db/risk_mvp.sqlite`
- Tabelas principais:
  - `monthly_observations`
  - `historical_predictions`
  - `model_metrics`

## Configuracao de fontes

Por padrao o sistema exige dados reais e falha se as fontes nao estiverem configuradas:

- `BCB_TARGET_SERIES_CODE`
- `BCB_NORTH_PROXY_SERIES_CODE`
- `SIDRA_AM_URL`
- `CAGED_AM_CSV_URL`

Fallback sintetico so e permitido de forma explicita para desenvolvimento:

- `ALLOW_SYNTHETIC_DATA=1`
- apenas quando `APP_ENV` for `dev`, `local` ou `test`

Use o template `./.env.example` para preencher as variaveis necessarias. Nao versione seu arquivo `.env` com credenciais ou URLs internas.

## Seguranca e publicacao

- Este repositorio inclui apenas o template `.env.example`.
- Arquivos locais de banco, artefatos, caches e dados foram excluidos do versionamento.
- Revise qualquer configuracao real antes de expor novas variaveis de ambiente ou fontes privadas.
