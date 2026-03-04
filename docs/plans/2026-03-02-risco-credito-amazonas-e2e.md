# Plano E2E — Risco de Credito com Dados Publicos (BCB + Amazonas)

**Data:** 2026-03-02  
**Objetivo:** Construir um MVP end-to-end para nowcasting mensal de risco de credito com dados publicos, usando base do BCB e recorte Amazonas.

## 1. Resumo Executivo

O projeto tera arquitetura completa de ponta a ponta com:

1. Ingestao de dados publicos (`BCB`, `IBGE SIDRA`, `CAGED`).
2. Pipeline mensal de preparacao e features.
3. Modelo baseline para nowcasting de inadimplencia.
4. API (`FastAPI`) para predicao e consulta historica.
5. Dashboard (`Streamlit`) para visualizacao e uso operacional.
6. Execucao local com `Docker Compose`.

Criterio principal de aceite do MVP: **MAE**.

---

## 2. Escopo

### In-scope

1. Coleta automatizada de series publicas.
2. Construcao de dataset mensal consolidado.
3. Treino e avaliacao de modelo baseline.
4. Exposicao de endpoints de inferencia e historico.
5. Dashboard funcional consumindo a API.
6. Testes unitarios, integracao e smoke E2E.

### Out-of-scope (MVP)

1. Deploy em cloud.
2. Dados privados de bureau.
3. Ensemble de modelos.
4. Monitoramento avancado em producao.
5. Explicabilidade avancada.

---

## 3. Decisoes Fechadas

1. **Stack:** Python + FastAPI + Streamlit.
2. **Execucao:** Local com Docker Compose.
3. **Horizonte:** Nowcasting mensal.
4. **Alvo:** Inadimplencia agregada (proxy de risco de credito).
5. **Recorte Amazonas:** Mistura de proxy da Regiao Norte + variaveis estaduais do AM.
6. **Fontes complementares AM:** IBGE SIDRA + CAGED.
7. **Metrica principal:** MAE.

---

## 4. Arquitetura Proposta

1. **Ingestion Layer**
   - Cliente BCB (series de credito/inadimplencia).
   - Cliente SIDRA (indicadores economicos do AM).
   - Cliente CAGED (mercado de trabalho do AM).

2. **Processing Layer**
   - Padronizacao temporal mensal.
   - Join por `ano_mes`.
   - Tratamento de faltantes e outliers.
   - Geracao de lags e medias moveis.

3. **Model Layer**
   - Baseline `ElasticNet`.
   - Validacao temporal (TimeSeriesSplit).
   - Persistencia de artefatos (`joblib`) e metricas.

4. **Serving Layer**
   - API FastAPI para health, execucao pipeline e predicao.

5. **Presentation Layer**
   - Streamlit para historico, nowcast e drivers.

6. **Ops Layer**
   - Docker Compose com servicos `api`, `app`, `scheduler`, `db`.

---

## 5. Interfaces Publicas

### Endpoints

1. `GET /health`
   - Retorna status, versao e timestamp.

2. `POST /pipeline/run`
   - Executa ingestao, processamento e treino.

3. `POST /predict/nowcast`
   - Entrada:
     - `reference_month` (`YYYY-MM`)
     - `features_override` (opcional)
   - Saida:
     - valor previsto da inadimplencia
     - faixa de confianca
     - variaveis com maior impacto

4. `GET /series/target?from=YYYY-MM&to=YYYY-MM`
   - Retorna serie historica observada e prevista.

### Schemas principais

1. `MonthlyObservation`
   - `year_month`
   - `target_default_rate`
   - `north_proxy`
   - `am_features`

2. `ModelMetrics`
   - `mae`
   - `rmse`
   - janelas de treino/validacao

3. `NowcastResponse`
   - `reference_month`
   - `y_hat`
   - `lower`, `upper`
   - `drivers[]`

---

## 6. Estrutura de Diretorios

```text
project/
  src/
    ingestion/
      bcb_client.py
      sidra_client.py
      caged_client.py
    processing/
      align.py
      features.py
      quality.py
    modeling/
      train.py
      predict.py
      evaluate.py
      registry.py
    api/
      main.py
      schemas.py
      routes/
    app/
      streamlit_app.py
    jobs/
      run_pipeline.py
  tests/
    unit/
    integration/
    e2e/
  infra/
    docker-compose.yml
    Dockerfile.api
    Dockerfile.app
  data/
    raw/
    processed/
    artifacts/
```

---

## 7. Plano de Execucao (AGILE)

1. **Analyze**
   - Validar disponibilidade de series do BCB uteis ao alvo.
   - Identificar variaveis AM no SIDRA/CAGED.
   - Documentar limitacoes do recorte estadual.

2. **Plan**
   - Quebrar backlog em blocos: infra, dados, modelo, API, dashboard, testes.
   - Definir entregaveis minimos por bloco.

3. **Design**
   - Fechar contratos de API e schemas.
   - Definir logica de pipeline mensal e versionamento de artefatos.

4. **Build**
   - Implementar conectores.
   - Implementar transformacao/feature engineering.
   - Treinar baseline.
   - Expor endpoints e construir dashboard.

5. **Test**
   - Executar unitarios e integracao.
   - Validar E2E com `docker compose up`.
   - Verificar MAE e consistencia dos endpoints.

6. **Review**
   - Revisar qualidade de codigo, riscos de dados e comportamento temporal.
   - Registrar limitacoes e acoes pos-MVP.

7. **Launch**
   - Publicar instrucoes de execucao local.
   - Validar checklist final de aceite.
   - Congelar versao MVP.

---

## 8. Testes e Criterios de Aceite

### Unitarios

1. Parse e normalizacao de datas.
2. Calculo de features (lags/medias).
3. Validacao de schemas de entrada/saida.

### Integracao

1. Conectores retornam datasets no formato esperado.
2. Pipeline completo gera dataset processado e artefatos.

### E2E

1. Servicos sobem com Docker Compose.
2. `POST /pipeline/run` executa sem erro.
3. `POST /predict/nowcast` retorna resposta valida.
4. Dashboard apresenta historico e previsao.

### Aceite final do MVP

1. Pipeline mensal reproduzivel.
2. API funcional com endpoints definidos.
3. Dashboard operacional.
4. Metrica MAE calculada e registrada.

---

## 9. Riscos e Mitigacoes

1. **Cobertura insuficiente estadual no BCB**
   - Mitigacao: usar proxy Regiao Norte + variaveis AM.

2. **Mudancas de formato em fontes publicas**
   - Mitigacao: camada de adapter por fonte + validacao de schema.

3. **Series curtas para treino**
   - Mitigacao: baseline simples, regularizacao e validacao temporal conservadora.

4. **Drift temporal**
   - Mitigacao: re-treino periodico e monitoramento basico da metrica.

---

## 10. Assuncoes e Defaults

1. Frequencia padrao mensal.
2. Baseline inicial unico: ElasticNet.
3. Banco inicial: SQLite.
4. Execucao inicial manual do pipeline.
5. Projeto local-first, sem cloud no MVP.
