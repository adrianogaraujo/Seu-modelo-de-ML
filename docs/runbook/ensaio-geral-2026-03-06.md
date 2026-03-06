# Ensaio Geral - 2026-03-06

## Objetivo
Validar que o repositorio esta pronto para gravacao de aulas com fluxo real e fluxo em snapshot.

## Evidencias executadas
1. `python -m unittest discover -s tests`
- Resultado: `33 tests` passando.

2. Validacao real de fontes
- Comando: chamada de `validate_sources` com `.env`.
- Resultado: `status=ok`.

3. Pipeline e aceite real
- Comando: `run_pipeline` + `run_real_acceptance`.
- Resultado: `status=ok`, readiness `warn` (continuar com cautela).

4. Snapshot de aula
- Comando: `python scripts/create_snapshot.py --name 2026-03-06-course-baseline`.
- Resultado: snapshot criado em `data/snapshots/2026-03-06-course-baseline`.

5. Bootstrap em modo snapshot
- Comando: `.\scripts\bootstrap_aula.ps1 -Mode snapshot -Snapshot 2026-03-06-course-baseline`.
- Resultado: smoke da API com `/health=200`, `/pipeline/readiness=200`, `/predict/nowcast=200`.

6. Bootstrap em modo real
- Comando: `.\scripts\bootstrap_aula.ps1 -Mode real`.
- Resultado: `source_validation.status=ok`, pipeline `status=ok`, smoke da API com endpoints principais respondendo.

## Conclusao
Projeto aprovado para gravacao de temporada inicial para iniciantes, com operacao reprodutivel em snapshot e caminho real validado.
