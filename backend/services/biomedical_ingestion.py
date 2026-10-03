from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from services.master_registry import (
    clear_registry_cache,
    hydrate_fda_approved_drugs,
    hydrate_mondo_all_diseases,
    hydrate_mondo_rare_diseases,
    hydrate_pubchem_seed_compounds,
    hydrate_rxterms_drugs,
    registry_data_depth,
    registry_source_manifest,
)

ProgressCallback = Optional[Callable[[Dict[str, Any]], None]]


def _emit(progress_callback: ProgressCallback, payload: Dict[str, Any]) -> None:
    if progress_callback is None:
        return
    try:
        progress_callback(payload)
    except Exception:
        pass


def _run_step(
    step: str,
    fn: Callable[[], Dict[str, Any]],
    *,
    progress_callback: ProgressCallback = None,
    continue_on_error: bool = True,
) -> Dict[str, Any]:
    started_at = time.time()
    _emit(progress_callback, {"event": "step_started", "step": step, "started_at": started_at})
    try:
        payload = fn() or {}
        if not isinstance(payload, dict):
            payload = {"result": payload}
        result = {
            "step": step,
            "ok": bool(payload.get("ok", True)),
            "elapsed_sec": round(time.time() - started_at, 2),
            **payload,
        }
        _emit(progress_callback, {"event": "step_finished", **result})
        return result
    except Exception as exc:
        result = {
            "step": step,
            "ok": False,
            "error": str(exc),
            "elapsed_sec": round(time.time() - started_at, 2),
        }
        _emit(progress_callback, {"event": "step_failed", **result})
        if continue_on_error:
            return result
        raise



def hydrate_full_biomedical_ingestion(
    *,
    include_mondo_all: bool = True,
    include_mondo_rare: bool = True,
    include_fda: bool = True,
    include_rxterms: bool = True,
    include_pubchem_seed_compounds: bool = True,
    mondo_download_url: Optional[str] = None,
    mondo_rare_download_url: Optional[str] = None,
    pubchem_seed_names: Optional[List[str]] = None,
    progress_callback: ProgressCallback = None,
    continue_on_error: bool = True,
) -> Dict[str, Any]:
    started_at = time.time()
    steps: List[Dict[str, Any]] = []

    if include_mondo_all:
        steps.append(
            _run_step(
                'mondo_all',
                lambda: hydrate_mondo_all_diseases(download_url=mondo_download_url),
                progress_callback=progress_callback,
                continue_on_error=continue_on_error,
            )
        )
    if include_mondo_rare:
        steps.append(
            _run_step(
                'mondo_rare',
                lambda: hydrate_mondo_rare_diseases(download_url=mondo_rare_download_url),
                progress_callback=progress_callback,
                continue_on_error=continue_on_error,
            )
        )
    if include_fda:
        steps.append(
            _run_step(
                'openfda',
                hydrate_fda_approved_drugs,
                progress_callback=progress_callback,
                continue_on_error=continue_on_error,
            )
        )
    if include_rxterms:
        steps.append(
            _run_step(
                'rxterms',
                hydrate_rxterms_drugs,
                progress_callback=progress_callback,
                continue_on_error=continue_on_error,
            )
        )
    if include_pubchem_seed_compounds:
        steps.append(
            _run_step(
                'pubchem_seed',
                lambda: hydrate_pubchem_seed_compounds(seed_names=pubchem_seed_names or []),
                progress_callback=progress_callback,
                continue_on_error=continue_on_error,
            )
        )

    clear_registry_cache()
    depth = registry_data_depth()
    manifest = registry_source_manifest()
    failed_steps = [step.get('step') or step.get('source') or 'unknown' for step in steps if step.get('ok') is False]
    payload = {
        'ok': not failed_steps,
        'steps': steps,
        'failed_steps': failed_steps,
        'depth': depth,
        'manifest': manifest,
        'elapsed_sec': round(time.time() - started_at, 2),
    }
    _emit(progress_callback, {'event': 'all_finished', **payload})
    return payload
