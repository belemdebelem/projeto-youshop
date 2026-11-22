from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


@dataclass(frozen=True)
class Settings:
    project_root: Path
    data_raw_dir: Path
    data_bronze_dir: Path
    data_exports_dir: Path
    duckdb_path: Path
    default_seed: int
    amount_tolerance: float
    payout_match_window_days: int
    anomaly_contamination: float
    priority_w_financial: float
    priority_w_anomaly: float
    priority_w_urgency: float
    enable_llm: bool


def get_settings() -> Settings:
    root = Path(__file__).resolve().parents[2]
    _load_dotenv(root / ".env")

    def p(name: str, default: str) -> Path:
        value = Path(os.getenv(name, default))
        return value if value.is_absolute() else root / value

    return Settings(
        project_root=root,
        data_raw_dir=p("DATA_RAW_DIR", "data/raw"),
        data_bronze_dir=p("DATA_BRONZE_DIR", "data/bronze"),
        data_exports_dir=p("DATA_EXPORTS_DIR", "data/exports"),
        duckdb_path=p("DUCKDB_PATH", "data/duckdb/youshop_finance.duckdb"),
        default_seed=int(os.getenv("DEFAULT_SEED", "42")),
        amount_tolerance=float(os.getenv("AMOUNT_TOLERANCE", "0.01")),
        payout_match_window_days=int(os.getenv("PAYOUT_MATCH_WINDOW_DAYS", "3")),
        anomaly_contamination=float(os.getenv("ANOMALY_CONTAMINATION", "0.05")),
        priority_w_financial=float(os.getenv("PRIORITY_W_FINANCIAL", "0.5")),
        priority_w_anomaly=float(os.getenv("PRIORITY_W_ANOMALY", "0.3")),
        priority_w_urgency=float(os.getenv("PRIORITY_W_URGENCY", "0.2")),
        enable_llm=os.getenv("ENABLE_LLM", "false").lower() == "true",
    )
