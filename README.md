# Risco de Credito Amazonas MVP

MVP local-first para nowcasting mensal de inadimplencia com recorte Amazonas.

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

Valide fontes reais sem treino:
- `GET /pipeline/validate-sources`

Rodar checklist de aceite em dados reais (valida fontes + executa pipeline + checa artefatos):
- `POST /pipeline/run-real-acceptance`
- ou CLI: `python -m src.jobs.run_real_acceptance`

Monitoramento basico de qualidade de dados (sem treino):
- `GET /pipeline/data-quality`

## Persistencia

- Banco SQLite local: `data/db/risk_mvp.sqlite`
- Tabelas principais:
  - `monthly_observations`
  - `historical_predictions`
  - `model_metrics`

## Ingestao real (padrao estrito)

Por padrao o sistema exige dados reais e falha se as fontes nao estiverem configuradas:

- `BCB_TARGET_SERIES_CODE`: codigo SGS para alvo de inadimplencia.
- `BCB_NORTH_PROXY_SERIES_CODE`: codigo SGS para proxy da regiao Norte.
- `SIDRA_AM_URL`: URL da consulta SIDRA ja filtrada para AM e frequencia mensal.
- `CAGED_AM_CSV_URL`: URL CSV com colunas `year_month` e `am_net_jobs`.

Fallback sintetico so e permitido de forma explicita para desenvolvimento:

- `ALLOW_SYNTHETIC_DATA=1`
- e somente quando `APP_ENV` for `dev`, `local` ou `test` (em `prod` e bloqueado).

### Opcao A (selecionada)

- `BCB_TARGET_SERIES_CODE=21085`
- `BCB_NORTH_PROXY_SERIES_CODE=27125`
- `SIDRA_AM_URL=https://apisidra.ibge.gov.br/values/t/8880/n3/13/v/7169/p/all?formato=json`
- `CAGED_AM_CSV_URL`: definir URL CSV mensal AM normalizada (`year_month`, `am_net_jobs`).
- `CAGED_AM_XLSX_URL` (alternativo): link oficial mensal do Novo CAGED em XLSX. O parser tenta detectar automaticamente colunas como `UF/Estado`, `Competencia/Mes`, `Saldo` ou `Admissoes/Desligamentos`.

Use o template [`.env.example`](C:\Users\adriano\Documents\Seu modelo de ML está errado e você não sabe\project\.env.example) para preencher os valores.

Referências oficiais para CAGED:
- Página mensal (exemplo julho/2025): https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/estatisticas-trabalho/novo-caged/2025/julho/pagina-inicial
- Download direto do arquivo identificado nessa página (exemplo): `https://drive.google.com/uc?export=download&id=1ur1_lVFTHOqE0ANEKch0L7cP2ylCJO6J`
