"""Turns the request from Business Central into the report rows."""
import logging

from recon_ai import generate_descriptions


def _order(source: dict, index: int):
    is_exact = source["source_type"].lower() == "exact"
    is_adjustment = source["source_table"].lower().startswith("duplicates removed")
    return (0 if is_exact and not is_adjustment else 1 if is_exact else 2, index)


def build_rows(payload: dict) -> list:
    tables = payload.get("tables", [])
    descriptions = generate_descriptions(tables, payload.get("knowledge_prefix", ""))
    modules = sorted({t.get("module", "") for t in tables})
    logging.info("Reconciliation request: %d tables, modules received: %s, client_build=%s",
                 len(tables), modules, payload.get("client_build", "(none)"))
    if modules == [""]:
        logging.warning("No 'module' in the request - the Business Central extension sending it is not deployed; "
                        "every table will be listed under 'Other Modules'")
    rows = []
    for t in tables:
        sources = t.get("sources", [])
        exact_total = sum(s["total_source_table_count"] for s in sources if s["source_type"].lower() == "exact")
        # Staging count comes from the Migration Checklist when the table was migrated; Phase 1 count otherwise
        staging_count = t["mt_table_count"] if t.get("in_checklist") else t["mig_staging_table_count"]
        ordered = [s for _, s in sorted(((_order(s, i), s) for i, s in enumerate(sources)), key=lambda x: x[0])]
        for s in ordered:
            condition, scope = descriptions.get((t["mig_staging_table"], s["source_table"]), ("", ""))
            rows.append({
                "module": t.get("module", ""),
                "source_table": s["source_table"],
                "source_type": s["source_type"],
                "source_count": s["total_source_table_count"],
                "source_total": exact_total,
                "mig_table": t["mig_staging_table"],
                "mig_count": staging_count,
                "qcore_table": t.get("qcore_table_name", ""),
                "success": t.get("migrated_successfully", 0),
                "failed": t.get("migrated_failed", 0),
                "condition": condition,
                "scope": scope,
                "remark": "",
            })
    return rows
