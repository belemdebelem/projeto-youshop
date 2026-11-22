from __future__ import annotations

import json
from dataclasses import dataclass

import pandas as pd


@dataclass
class Brief:
    case_id: str
    provider: str
    brief_text: str
    evidence_refs: list[str]
    is_assistive: bool = True


class TemplateProvider:
    name = "template"

    def explain(self, case: pd.Series) -> Brief:
        status = case.get("reconciliation_status")
        rule = case.get("match_rule")
        expected = case.get("expected_amount")
        actual = case.get("actual_amount")
        diff = case.get("diff_amount")
        a = f"{case.get('entity_a_type')}:{case.get('entity_a_id')}"
        b = f"{case.get('entity_b_type')}:{case.get('entity_b_id')}"
        evidence = [str(case.get("entity_a_id")), str(case.get("entity_b_id"))]
        text = (
            f"[Assistivo] Caso {case.get('case_id')} ({rule}, {status}). "
            f"Evidência: {a} vs {b}; esperado={expected}; encontrado={actual}; diff={diff}. "
            f"Ação sugerida: validar origem dos registros, confirmar regra aplicada e registrar decisão do analista. "
            f"Nenhum valor foi calculado por LLM e nenhuma ação financeira automática foi executada."
        )
        return Brief(case_id=str(case.get("case_id")), provider=self.name, brief_text=text, evidence_refs=evidence)


def build_case_briefs(run_id: str, recon: pd.DataFrame) -> pd.DataFrame:
    provider = TemplateProvider()
    rows = []
    for _, c in recon[recon["reconciliation_status"] != "matched"].iterrows():
        b = provider.explain(c)
        rows.append({
            "brief_id": f"{run_id}:{b.case_id}",
            "case_id": b.case_id,
            "run_id": run_id,
            "provider": b.provider,
            "brief_text": b.brief_text,
            "evidence_refs_json": json.dumps(b.evidence_refs, ensure_ascii=False),
            "is_assistive": b.is_assistive,
            "created_at": pd.Timestamp.utcnow().isoformat(),
        })
    return pd.DataFrame(rows)
