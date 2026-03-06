# Modulos Didaticos para Iniciantes

## Modulo 1: Contexto de negocio e alvo
- Objetivo: explicar inadimplencia, nowcasting e por que previsao mensal importa.
- Demo: leitura do endpoint `/health` e visão geral da arquitetura.
- Resultado esperado: aluno entende problema, target e escopo do MVP.

## Modulo 2: Ingestao de dados reais
- Objetivo: mostrar de onde vem cada fonte e como validar disponibilidade.
- Demo: `GET /pipeline/validate-sources`.
- Resultado esperado: aluno entende `status=ok`, janela e proveniencia.

## Modulo 3: Qualidade e alinhamento temporal
- Objetivo: ensinar risco de buracos, duplicidade e sobreposicao entre fontes.
- Demo: `GET /pipeline/data-quality`.
- Resultado esperado: aluno interpreta `overlap_ratio` e status por fonte.

## Modulo 4: Feature engineering de baseline
- Objetivo: apresentar lag e media movel como baseline interpretavel.
- Demo: inspecao de `data/processed/monthly_dataset.csv`.
- Resultado esperado: aluno entende o que o modelo realmente enxerga.

## Modulo 5: Treino e metricas
- Objetivo: explicar ElasticNet e validacao temporal.
- Demo: `POST /pipeline/run` e leitura de `metrics`.
- Resultado esperado: aluno entende `mae`, `rmse` e limites do baseline.

## Modulo 6: Readiness e aceite minimo
- Objetivo: ensinar gates objetivos para liberar ou barrar uso de MVP.
- Demo: `GET /pipeline/readiness` e `POST /pipeline/run-real-acceptance`.
- Resultado esperado: aluno diferencia `pass`, `warn`, `fail`.

## Modulo 7: Inferencia e interpretabilidade
- Objetivo: mostrar nowcast com intervalo e principais drivers.
- Demo: `POST /predict/nowcast`.
- Resultado esperado: aluno entende resposta e leitura dos drivers.

## Modulo 8: Produto local (API + dashboard)
- Objetivo: conectar engenharia e entrega para uso prático.
- Demo: API em FastAPI + dashboard em Streamlit.
- Resultado esperado: aluno consegue reproduzir demo de ponta a ponta.
