# Runbook de Preparacao para Gravacao

## Checklist tecnico minimo
1. `python -m unittest discover -s tests`
2. `python -m src.jobs.run_pipeline`
3. `python -m src.jobs.run_real_acceptance`
4. `python scripts/create_snapshot.py --name <snapshot>`
5. `.\scripts\bootstrap_aula.ps1 -Mode snapshot -Snapshot <snapshot>`

## Comandos recomendados

```powershell
copy .env.example .env
python -m unittest discover -s tests
python -m src.jobs.run_pipeline
python -m src.jobs.run_real_acceptance
python scripts/create_snapshot.py --name 2026-03-06-course-baseline
.\scripts\bootstrap_aula.ps1 -Mode snapshot -Snapshot 2026-03-06-course-baseline
```

## Evidencias para anexar na aula
- Saida do aceite real com `status=ok`.
- `metrics.json` do baseline.
- Resultado do smoke test da API.
- Nome e data do snapshot utilizado.
