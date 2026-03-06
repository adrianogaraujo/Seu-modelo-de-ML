from __future__ import annotations

# %% Imports and Project Bootstrap
# Esta celula apenas prepara os imports e aponta o Python para `project/`.
# Resultado esperado: nenhum output e nenhuma excecao.
# Pare aqui se algum import falhar, porque o caminho do projeto ainda nao esta utilizavel.
import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

def _detect_workspace_root() -> Path:
    # Running as a script
    if "__file__" in globals():
        return Path(__file__).resolve().parent

    # Running in REPL/Notebook/PyCharm console where __file__ is absent
    candidates: list[Path] = [Path.cwd().resolve()]
    for entry in sys.path:
        if not entry:
            continue
        try:
            candidate = Path(entry).resolve()
        except Exception:
            continue
        candidates.append(candidate)

    for candidate in candidates:
        project_dir = candidate / "project"
        if project_dir.exists() and (project_dir / "src").exists():
            return candidate

    return Path.cwd().resolve()


WORKSPACE_ROOT = _detect_workspace_root()
PROJECT_ROOT = WORKSPACE_ROOT / "project"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.jobs.data_quality_report import run_data_quality_report  # noqa: E402
from src.jobs.readiness_assessment import assess_readiness_from_artifacts, assess_readiness_from_run  # noqa: E402
from src.jobs.run_pipeline import run_pipeline  # noqa: E402
from src.jobs.validate_sources import validate_sources  # noqa: E402
from src.modeling.registry import load_model  # noqa: E402


def _load_env_file(path: Path) -> bool:
    if not path.exists():
        return False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key and key not in os.environ:
            os.environ[key] = value
    return True


def _bootstrap_environment() -> Dict[str, Any]:
    env_project = PROJECT_ROOT / ".env"
    env_workspace = WORKSPACE_ROOT / ".env"
    example_project = PROJECT_ROOT / ".env.example"
    example_workspace = WORKSPACE_ROOT / ".env.example"

    loaded = []
    for candidate in (env_project, env_workspace, example_project, example_workspace):
        if _load_env_file(candidate):
            loaded.append(str(candidate))
            break

    return {
        "loaded_files": loaded,
        "used_fallback_example": any(path.endswith(".env.example") for path in loaded),
    }


BOOTSTRAP_ENV_INFO = _bootstrap_environment()


# %% Constants and Data Contracts
# Essas variaveis globais permitem rodar uma celula por vez e inspecionar resultados intermediarios.
# Resultado esperado: as variaveis de estado comecam como `None` e vao sendo preenchidas ao longo da execucao.
REQUIRED_ENV_VARS = (
    "BCB_TARGET_SERIES_CODE",
    "BCB_NORTH_PROXY_SERIES_CODE",
    "SIDRA_AM_URL",
)
OPTIONAL_ENV_GROUPS = (("CAGED_AM_CSV_URL", "CAGED_AM_XLSX_URL"),)
ACTIVE_PROJECT_ROOT = PROJECT_ROOT

ENVIRONMENT_SNAPSHOT: Dict[str, Any] | None = None
SOURCE_VALIDATION_RESULT: Dict[str, Any] | None = None
DATA_QUALITY_RESULT: Dict[str, Any] | None = None
PIPELINE_RESULT: Dict[str, Any] | None = None
ARTIFACT_SNAPSHOT: Dict[str, Any] | None = None
READINESS_RESULT: Dict[str, Any] | None = None
FINAL_REPORT: "ReproducibilityReport | None" = None


@dataclass
class ReproducibilityReport:
    generated_at_utc: str
    workspace_root: str
    project_root: str
    python_version: str
    environment: Dict[str, Any]
    source_validation: Dict[str, Any]
    data_quality: Dict[str, Any]
    pipeline: Dict[str, Any]
    artifacts: Dict[str, Any]
    readiness: Dict[str, Any]
    replication_steps: list[str]


# %% Environment Validation Helpers
def _required_env_snapshot() -> Dict[str, Any]:
    # Este helper nao consulta nenhuma fonte externa.
    # Ele apenas verifica se a configuracao minima para dados reais esta presente.
    values: Dict[str, Any] = {}
    missing: list[str] = []

    for name in REQUIRED_ENV_VARS:
        value = os.getenv(name, "").strip()
        values[name] = value
        if not value:
            missing.append(name)

    caged_group = {name: os.getenv(name, "").strip() for name in OPTIONAL_ENV_GROUPS[0]}
    values.update(caged_group)
    if not any(caged_group.values()):
        missing.append("CAGED_AM_CSV_URL|CAGED_AM_XLSX_URL")

    return {
        "app_env": os.getenv("APP_ENV", "prod").strip() or "prod",
        "required_values": values,
        "missing": missing,
        "is_ready": not missing,
    }


# %% Step 1 - Select Project Root
# Rode esta etapa primeiro se quiser apontar o fluxo para outro clone/caminho.
# Resultado esperado: um caminho absoluto para o diretorio ativo do projeto.
# Pare se o caminho estiver errado, porque todas as proximas etapas leem ou escrevem nele.
def set_active_project_root(project_root: str | Path) -> Path:
    global ACTIVE_PROJECT_ROOT
    ACTIVE_PROJECT_ROOT = Path(project_root).resolve()
    return ACTIVE_PROJECT_ROOT


# %% Step 2 - Validate Environment Readiness
# Rode esta etapa antes de consultar qualquer fonte.
# Resultado esperado: `is_ready=True` e `missing=[]`.
# Pare se `is_ready=False`; isso indica falha de configuracao, nao falha das fontes reais.
def check_environment_readiness() -> Dict[str, Any]:
    global ENVIRONMENT_SNAPSHOT
    ENVIRONMENT_SNAPSHOT = _required_env_snapshot()
    return ENVIRONMENT_SNAPSHOT


# %% Artifact Inspection Helpers
def _artifact_snapshot(project_root: Path) -> Dict[str, Any]:
    # Este helper le os outputs locais depois que o pipeline roda.
    # Use para confirmar que o modelo foi persistido e marcado explicitamente como dado real.
    artifact_dir = project_root / "data" / "artifacts"
    model_path = artifact_dir / "baseline_model.joblib"
    metrics_path = artifact_dir / "metrics.json"
    history_path = project_root / "data" / "processed" / "historical_predictions.csv"
    dataset_path = project_root / "data" / "processed" / "monthly_dataset.csv"
    db_path = project_root / "data" / "db" / "risk_mvp.sqlite"

    bundle: Dict[str, Any] | None = None
    if model_path.exists():
        bundle = load_model(model_path)

    metrics_payload: Dict[str, Any] | None = None
    if metrics_path.exists():
        metrics_payload = json.loads(metrics_path.read_text(encoding="utf-8"))

    return {
        "model_path": str(model_path),
        "model_exists": model_path.exists(),
        "model_data_mode": None if bundle is None else bundle.get("data_mode"),
        "model_data_provenance": None if bundle is None else bundle.get("data_provenance"),
        "metrics_path": str(metrics_path),
        "metrics_exists": metrics_path.exists(),
        "metrics_payload": metrics_payload,
        "history_path": str(history_path),
        "history_exists": history_path.exists(),
        "dataset_path": str(dataset_path),
        "dataset_exists": dataset_path.exists(),
        "db_path": str(db_path),
        "db_exists": db_path.exists(),
    }


# %% Step 3 - Validate Real Sources
# Este e o primeiro checkpoint com fontes externas.
# Resultado esperado: cada fonte retorna `mode=real`, `configured=True` e `rows>0`.
# Pare se alguma fonte levantar erro ou retornar uma janela inesperada; isso indica
# problema real de upstream, parsing ou configuracao.
def validate_real_sources(project_root: Path | None = None) -> Dict[str, Any]:
    global SOURCE_VALIDATION_RESULT
    target_root = ACTIVE_PROJECT_ROOT if project_root is None else Path(project_root).resolve()
    SOURCE_VALIDATION_RESULT = validate_sources(target_root)
    return SOURCE_VALIDATION_RESULT


# %% Step 4 - Run Data Quality Checks
# Rode esta etapa apenas depois da validacao das fontes.
# Resultado esperado: `status` idealmente `ok`; `warn` significa dado utilizavel com ressalvas.
# Pare em `fail`, ou em perda grande de sobreposicao / meses duplicados / datas invalidas,
# porque isso e sinal de problema real de integridade de dados, nao de modelagem.
def inspect_data_quality(project_root: Path | None = None) -> Dict[str, Any]:
    global DATA_QUALITY_RESULT
    target_root = ACTIVE_PROJECT_ROOT if project_root is None else Path(project_root).resolve()
    DATA_QUALITY_RESULT = run_data_quality_report(target_root)
    return DATA_QUALITY_RESULT


# %% Step 5 - Execute Training Pipeline
# Esta e a primeira etapa analitica com escrita em disco: ela grava dados processados e artefatos.
# Resultado esperado: `rows_raw` positivo, `rows_training` positivo e metricas presentes.
# Pare se a contagem de linhas colapsar ou se o pipeline falhar; isso normalmente indica
# baixa sobreposicao entre fontes, janela quebrada ou excesso de perda na geracao de features.
def execute_training_pipeline(project_root: Path | None = None) -> Dict[str, Any]:
    global PIPELINE_RESULT
    target_root = ACTIVE_PROJECT_ROOT if project_root is None else Path(project_root).resolve()
    PIPELINE_RESULT = run_pipeline(target_root)
    return PIPELINE_RESULT


# %% Step 6 - Inspect Persisted Artifacts
# Rode esta etapa depois do pipeline para confirmar persistencia, nao qualidade do modelo.
# Resultado esperado: modelo, metricas, historico, dataset e banco todos existentes.
# Pare se `model_data_mode` nao for `real` ou se algum artefato central estiver ausente,
# porque isso significa que a execucao ainda nao e reproduzivel para outro data scientist.
def inspect_artifacts(project_root: Path | None = None) -> Dict[str, Any]:
    global ARTIFACT_SNAPSHOT
    target_root = ACTIVE_PROJECT_ROOT if project_root is None else Path(project_root).resolve()
    ARTIFACT_SNAPSHOT = _artifact_snapshot(target_root)
    return ARTIFACT_SNAPSHOT


# %% Step 7 - Avaliar Prontidao Objetiva da Base
# Rode esta etapa depois de validar fontes, qualidade e pipeline.
# Resultado esperado: `status` em `pass`, `warn` ou `fail`, com checks explicitos.
# Pare se vier `fail`; nesse caso, a base atual nao deve ser tratada como pronta para conclusoes.
def assess_current_readiness(project_root: Path | None = None) -> Dict[str, Any]:
    global READINESS_RESULT
    target_root = ACTIVE_PROJECT_ROOT if project_root is None else Path(project_root).resolve()
    if SOURCE_VALIDATION_RESULT and DATA_QUALITY_RESULT and PIPELINE_RESULT:
        READINESS_RESULT = assess_readiness_from_run(
            source_validation=SOURCE_VALIDATION_RESULT,
            data_quality=DATA_QUALITY_RESULT,
            pipeline_result=PIPELINE_RESULT,
            project_root=target_root,
        )
    else:
        READINESS_RESULT = assess_readiness_from_artifacts(target_root)
    return READINESS_RESULT


# %% Replication Playbook
def _replication_steps(project_root: Path) -> list[str]:
    return [
        f"1. Create and activate a virtual environment inside {project_root}.",
        "2. Install dependencies with `pip install -r requirements.txt`.",
        "3. Fill `.env` from `.env.example` with real BCB, SIDRA and CAGED source values.",
        "4. Run this script to validate sources, inspect data quality and train the baseline in one pass.",
        "5. Confirm the final report shows `model_data_mode=real` and all sources with `mode=real`.",
        "6. Only after that, expose the API or share the generated artifacts with the team.",
    ]


# %% Step 8 - Build Final Reproducibility Report
# Esta etapa consolida as celulas anteriores em um unico objeto estruturado.
# Resultado esperado: um `ReproducibilityReport` completo, com evidencias de fontes reais.
# Se falhar, o estado anterior esta incompleto; inspecione as variaveis acima antes de seguir.
def build_reproducibility_report(project_root: Path | None = None) -> ReproducibilityReport:
    global FINAL_REPORT
    target_root = ACTIVE_PROJECT_ROOT if project_root is None else Path(project_root).resolve()
    env_snapshot = ENVIRONMENT_SNAPSHOT or check_environment_readiness()
    if not env_snapshot["is_ready"]:
        missing = ", ".join(env_snapshot["missing"])
        raise RuntimeError(
            f"Real-data environment is incomplete. Missing: {missing}. "
            "Fill the required variables before running the workflow."
        )

    source_validation = SOURCE_VALIDATION_RESULT or validate_real_sources(target_root)
    data_quality = DATA_QUALITY_RESULT or inspect_data_quality(target_root)
    pipeline_result = PIPELINE_RESULT or execute_training_pipeline(target_root)
    artifacts = ARTIFACT_SNAPSHOT or inspect_artifacts(target_root)
    readiness = READINESS_RESULT or assess_current_readiness(target_root)

    FINAL_REPORT = ReproducibilityReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        workspace_root=str(WORKSPACE_ROOT),
        project_root=str(target_root),
        python_version=sys.version.split()[0],
        environment=env_snapshot,
        source_validation=source_validation,
        data_quality=data_quality,
        pipeline=pipeline_result,
        artifacts=artifacts,
        readiness=readiness,
        replication_steps=_replication_steps(target_root),
    )
    return FINAL_REPORT


# %% Step 9 - Suggested Interactive Execution Order
# Esta e a ordem manual recomendada para execucao em estilo notebook.
# Se estiver depurando problema de fonte, pare assim que uma etapa trouxer dado inesperado
# em vez de continuar para as etapas de treino.
NOTEBOOK_SEQUENCE = [
    "ACTIVE_PROJECT_ROOT = set_active_project_root(PROJECT_ROOT)",
    "ENVIRONMENT_SNAPSHOT = check_environment_readiness()",
    "SOURCE_VALIDATION_RESULT = validate_real_sources()",
    "DATA_QUALITY_RESULT = inspect_data_quality()",
    "PIPELINE_RESULT = execute_training_pipeline()",
    "ARTIFACT_SNAPSHOT = inspect_artifacts()",
    "READINESS_RESULT = assess_current_readiness()",
    "FINAL_REPORT = build_reproducibility_report()",
    "_print_report(FINAL_REPORT)",
]


# %% End-to-End Reproducible Workflow
# Este e o caminho de execucao em uma passada so para CLI.
# Ele roda a mesma sequencia das celulas, mas sem checkpoints manuais.
def run_reproducible_analysis(project_root: Path) -> ReproducibilityReport:
    set_active_project_root(project_root)
    check_environment_readiness()
    validate_real_sources(project_root)
    inspect_data_quality(project_root)
    execute_training_pipeline(project_root)
    inspect_artifacts(project_root)
    assess_current_readiness(project_root)
    return build_reproducibility_report(project_root)


# %% Structured Reporting
# Use esta etapa depois que `FINAL_REPORT` existir.
# Ela imprime um resumo curto primeiro e depois o JSON completo para auditoria.
def _print_report(report: ReproducibilityReport) -> None:
    payload = asdict(report)
    print("=== Reproducible Credit Risk Run ===")
    print(f"generated_at_utc: {payload['generated_at_utc']}")
    print(f"project_root: {payload['project_root']}")
    print(f"python_version: {payload['python_version']}")
    print(f"app_env: {payload['environment']['app_env']}")
    if BOOTSTRAP_ENV_INFO["loaded_files"]:
        print(f"env_bootstrap: loaded_from={BOOTSTRAP_ENV_INFO['loaded_files'][0]}")
    else:
        print("env_bootstrap: no .env/.env.example found; using process environment only")
    print("sources:")
    for name, meta in payload["source_validation"]["sources"].items():
        print(
            f"  - {name}: mode={meta['mode']} rows={meta['rows']} "
            f"window={meta['min_month']}..{meta['max_month']}"
        )
    print(
        "pipeline:"
        f" rows_raw={payload['pipeline']['rows_raw']}"
        f" rows_training={payload['pipeline']['rows_training']}"
        f" mae={payload['pipeline']['metrics'].get('mae')}"
        f" rmse={payload['pipeline']['metrics'].get('rmse')}"
    )
    print(
        "artifacts:"
        f" model_exists={payload['artifacts']['model_exists']}"
        f" history_exists={payload['artifacts']['history_exists']}"
        f" data_mode={payload['artifacts']['model_data_mode']}"
    )
    print(
        "readiness:"
        f" status={payload['readiness']['status']}"
        f" recommendation={payload['readiness']['recommendation']}"
    )
    print("report_json:")
    print(json.dumps(payload, indent=2, ensure_ascii=True))


# %% CLI Entrypoint
# Isso mantem o script utilizavel tanto como arquivo em estilo notebook quanto como CLI normal.
def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Executa o fluxo ponta a ponta com dados reais para o MVP de risco de credito "
            "e gera um relatorio de reprodutibilidade para outros data scientists."
        )
    )
    parser.add_argument(
        "--project-root",
        default=str(PROJECT_ROOT),
        help="Caminho para o diretorio do projeto que contem src/, tests/ e data/.",
    )
    parser.add_argument(
        "--write-report",
        default="",
        help=(
            "Caminho opcional para salvar o relatorio em JSON. Se omitido, o script "
            "apenas imprime o relatorio estruturado na saida padrao."
        ),
    )
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    report = run_reproducible_analysis(project_root)
    _print_report(report)

    if args.write_report:
        output_path = Path(args.write_report).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(asdict(report), indent=2, ensure_ascii=True),
            encoding="utf-8",
        )
        print(f"saved_report: {output_path}")

    return 0


# %% Interpretacao Rapida dos Resultados
# Use estas referencias para decidir se deve continuar, investigar ou parar a execucao.
# 1. `ENVIRONMENT_SNAPSHOT["is_ready"]` deve ser `True`.
#    Se for `False`, corrija as variaveis de ambiente antes de qualquer outra etapa.
# 2. Em `SOURCE_VALIDATION_RESULT`, cada fonte deve vir com `mode=real` e `rows>0`.
#    Se alguma fonte vier vazia, isso e problema real da fonte ou da janela consultada.
# 3. Em `DATA_QUALITY_RESULT`, `status="ok"` e o ideal.
#    `status="warn"` merece revisao. `status="fail"` deve bloquear a continuidade.
# 4. Em `READINESS_RESULT`, o status final deve ser:
#    `pass` para seguir, `warn` para seguir com cautela, `fail` para parar e investigar.
# 5. `READINESS_RESULT["summary"]["overlap_ratio"]` abaixo de `0.80` indica baixa sobreposicao.
#    Nessa situacao, o merge entre fontes fica fragil para um baseline confiavel.
# 6. `READINESS_RESULT["summary"]["rows_training"]` abaixo de `24` indica base insuficiente.
#    Entre `24` e `35`, a base ainda e fraca e entra em estado de alerta.
# 7. Em `ARTIFACT_SNAPSHOT`, `model_data_mode` deve ser `real`.
#    Se nao for, nao use a predicao nem compartilhe o artefato com outra pessoa.
# 8. `normalized_mae` e `normalized_rmse` sao os checks mais uteis para qualidade do baseline.
#    Mesmo assim, `pass` aqui ainda significa aceitavel para MVP, nao aprovacao de producao.

if __name__ == "__main__":
    raise SystemExit(main())
