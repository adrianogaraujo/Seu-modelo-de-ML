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
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python -m unittest discover -s tests
uvicorn src.api.main:app --reload
```

Em outro terminal, execute o dashboard:

```bash
streamlit run src/app/streamlit_app.py
```

Para rodar um alvo menor durante desenvolvimento:

```bash
python -m unittest tests.unit.test_features
```

## Arquivo unico portatil (roda sozinho)

Se voce quiser compartilhar apenas um arquivo para outra pessoa executar sem estrutura do projeto:

```bash
python "Seu modelo de ML está errado e você não sabe — análise de risco de crédito do zero.py"
```

Comportamento padrao:
- auto-instala dependencias faltantes;
- carrega `.env` local se existir (ou usa defaults embutidos);
- valida fontes reais, executa pipeline e readiness;
- salva relatorio em `portable_output/report-*.json`.

## Docker Compose

```bash
cd infra
docker compose up --build
```

Servicos:
- API: `http://localhost:8000`
- Dashboard: `http://localhost:8501`

## Endpoints uteis

- `GET /health`: retorna status, versao e timestamp.
- `POST /pipeline/run`: executa ingestao, processamento, treino e persistencia local com proveniencia real por fonte.
- `GET /pipeline/validate-sources`: valida fontes reais sem treino e retorna `mode=real` para cada fonte.
- `POST /pipeline/run-real-acceptance`: roda o checklist de aceite com fontes reais.
- `GET /pipeline/data-quality`: gera um resumo basico de qualidade de dados.
- `GET /pipeline/readiness`: avalia se a base e o baseline atual estao prontos para uso de MVP.
- `POST /predict/nowcast`: gera nowcast a partir de um artefato treinado e marcado como real.
- `GET /series/target?from=YYYY-MM&to=YYYY-MM`: retorna a serie historica observada e prevista.

Alternativa via CLI:

```bash
python -m src.jobs.run_real_acceptance
```

## Fluxo de aula (YouTube)

Para preparar e gravar aulas com reprodutibilidade:

1. Gere um baseline real:

```bash
python -m src.jobs.run_pipeline
python -m src.jobs.run_real_acceptance
```

2. Congele um snapshot local:

```bash
python scripts/create_snapshot.py --name 2026-03-06-course-baseline
```

3. Suba o projeto para aula em modo snapshot (sem depender de APIs externas):

```powershell
.\scripts\bootstrap_aula.ps1 -Mode snapshot -Snapshot 2026-03-06-course-baseline
```

4. Quando quiser atualizar com fontes reais:

```powershell
.\scripts\bootstrap_aula.ps1 -Mode real
```

## Desenvolvimento e TDD

O fluxo esperado de desenvolvimento e correcao neste repositorio e orientado por testes:

1. escreva ou ajuste primeiro um teste que falha e reproduz o comportamento desejado;
2. rode o menor escopo possivel (`tests.unit`, um modulo especifico, depois a suite completa);
3. implemente a menor mudanca necessaria para deixar o teste verde;
4. refatore somente depois que os testes relevantes estiverem passando.

Para bugs, comece por um teste de regressao. Para mudancas de comportamento, nao considere o trabalho concluido sem evidencia de teste correspondente.

Ao contribuir, mantenha os handlers da API enxutos e mova regras de negocio para `src/jobs`, `src/processing`, `src/modeling` ou `src/storage`, conforme a responsabilidade.

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
- `CAGED_AM_CSV_URL` ou `CAGED_AM_XLSX_URL`

O projeto nao possui fallback sintetico. Se qualquer fonte estiver ausente, vazia, fora da janela ou invalida, o pipeline falha explicitamente.
Para o caminho padrao de demo local, mantenha `CAGED_AM_CSV_URL` preenchida no `.env`.

O endpoint de readiness usa bandas objetivas:

- `pass`: pode seguir.
- `warn`: pode seguir com cautela.
- `fail`: pare e investigue.

Os thresholds atuais avaliam volume minimo por fonte, sobreposicao entre fontes, volume util de treino, artefato com `data_mode=real` e metricas normalizadas do baseline. Esse checklist vale para aceitacao do MVP, nao para aprovacao de producao regulatoria.

Use o template `./.env.example` para preencher as variaveis necessarias. Nao versione seu arquivo `.env` com credenciais ou URLs internas.

## Runbook de aceite minimo (Demo Local)

1. Preencha `./.env` (copiando de `.env.example`) com URLs/codigos reais das 3 fontes.
2. Rode pipeline completo:

```bash
python -m src.jobs.run_pipeline
```

3. Rode checklist de aceite real:

```bash
python -m src.jobs.run_real_acceptance
```

4. Com API no ar, valide endpoints:
   - `GET /pipeline/validate-sources`
   - `POST /pipeline/run`
   - `GET /pipeline/readiness`
   - `POST /predict/nowcast`
   - `GET /series/target?from=YYYY-MM&to=YYYY-MM`

### Criterio objetivo de viabilidade minima

- `validate-sources` retorna `status=ok`
- `run` retorna `rows_raw > 0` e `rows_training > 0`
- `readiness.status` e `pass` ou `warn` (nao `fail`)
- `predict/nowcast` retorna resposta valida com `data_mode=real`

## Seguranca e publicacao

- Este repositorio inclui apenas o template `.env.example`.
- Arquivos locais de banco, artefatos, caches e dados foram excluidos do versionamento.
- Revise qualquer configuracao real antes de expor novas variaveis de ambiente ou fontes privadas.
