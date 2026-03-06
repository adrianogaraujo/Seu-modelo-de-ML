# Kit de 8 Episodios (YouTube)

## Episodio 1 - O problema e a arquitetura
- Objetivo: apresentar o problema e o mapa do projeto.
- Demo curta: navegar em `src/` e testar `/health`.
- Takeaway: o aluno entende o fluxo ponta a ponta.

## Episodio 2 - Fontes reais sem fantasia
- Objetivo: configurar `.env` e validar fontes.
- Demo curta: `/pipeline/validate-sources`.
- Takeaway: dados reais exigem contrato e observabilidade.

## Episodio 3 - Qualidade de dados antes do modelo
- Objetivo: mostrar porque limpeza e sobreposicao mandam no resultado.
- Demo curta: `/pipeline/data-quality`.
- Takeaway: sem qualidade, modelo bonito engana.

## Episodio 4 - Features simples que funcionam
- Objetivo: construir intuicao para lag e media movel.
- Demo curta: `monthly_dataset.csv`.
- Takeaway: baseline explicavel vence overengineering no MVP.

## Episodio 5 - Treinando baseline com validacao temporal
- Objetivo: explicar treino com `TimeSeriesSplit`.
- Demo curta: `/pipeline/run` + metricas.
- Takeaway: metrica sem contexto temporal nao vale.

## Episodio 6 - Gate de readiness
- Objetivo: ensinar regra objetiva de seguir/parar.
- Demo curta: `/pipeline/readiness` e aceite real.
- Takeaway: decisao de deploy precisa de gate tecnico.

## Episodio 7 - Nowcast e drivers na pratica
- Objetivo: gerar previsao e interpretar fatores.
- Demo curta: `/predict/nowcast` e `/series/target`.
- Takeaway: previsao precisa ser consumivel por negocio.

## Episodio 8 - Fluxo de gravacao robusto (snapshot)
- Objetivo: mostrar como gravar sem quebrar ao vivo.
- Demo curta: `create_snapshot.py` + `bootstrap_aula.ps1`.
- Takeaway: creator tecnico precisa de reproducibilidade.

## Mini roteiro padrao por episodio
- Abertura (20-30s): problema do episodio e resultado final.
- Execucao (5-10min): 1 fluxo principal sem ramificacoes.
- Fechamento (30-60s): o que o aluno aprendeu e proximo passo.
