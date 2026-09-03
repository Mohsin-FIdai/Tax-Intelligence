"""
ETL Pipeline — Orchestrates ingestion, validation, cleaning, and storage of multi-source data.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from core.data_ingestion.schema_detector import detect_schema, detect_dataset_domain
from core.data_ingestion.data_validator import validate_dataframe
from core.data_ingestion.data_cleaner import clean_dataframe


class ETLPipeline:
    """End-to-end Extract–Transform–Load pipeline for tax intelligence data.

    Usage
    -----
    >>> pipeline = ETLPipeline(output_dir="data/processed")
    >>> pipeline.add_source("data/raw_uploads/tax_records.csv")
    >>> results = pipeline.run()
    """

    def __init__(
        self,
        output_dir: str | Path = "data/processed",
        on_progress: Callable[[str, float], None] | None = None,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._sources: list[dict[str, Any]] = []
        self._on_progress = on_progress or (lambda msg, pct: None)
        self._results: dict[str, dict] = {}

    # ── source management ───────────────────────────────────────────

    def add_source(self, filepath: str | Path, label: str | None = None) -> "ETLPipeline":
        """Register a data source file (CSV, XLSX, or JSON)."""
        fp = Path(filepath)
        if not fp.exists():
            raise FileNotFoundError(f"Source file not found: {fp}")
        self._sources.append({
            "path": fp,
            "label": label or fp.stem,
        })
        return self

    def add_sources_from_dir(self, directory: str | Path, extensions: tuple = (".csv", ".xlsx", ".json")) -> "ETLPipeline":
        """Add all files with matching extensions from a directory."""
        dirpath = Path(directory)
        for ext in extensions:
            for fp in sorted(dirpath.glob(f"*{ext}")):
                self.add_source(fp)
        return self

    # ── individual steps ────────────────────────────────────────────

    def ingest_file(self, filepath: Path) -> pd.DataFrame:
        """Read a file into a DataFrame based on its extension."""
        ext = filepath.suffix.lower()
        if ext == ".csv":
            return pd.read_csv(filepath, low_memory=False)
        elif ext in {".xlsx", ".xls"}:
            return pd.read_excel(filepath)
        elif ext == ".json":
            return pd.read_json(filepath)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    def validate(self, df: pd.DataFrame, label: str) -> dict:
        """Run validation and return a report dict."""
        report = validate_dataframe(df)
        return {
            "label": label,
            "total_rows": report.total_rows,
            "valid_rows": report.valid_rows,
            "validity_pct": report.validity_pct,
            "error_count": report.error_count,
            "errors_by_field": report.errors_by_field,
        }

    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and normalise the DataFrame."""
        return clean_dataframe(df)

    # ── full pipeline ───────────────────────────────────────────────

    def run(self) -> dict[str, dict]:
        """Execute the full ETL pipeline for all registered sources.

        Returns a dict keyed by source label with schema, validation, and output info.
        """
        if not self._sources:
            raise RuntimeError("No sources registered. Call add_source() first.")

        total = len(self._sources)
        results: dict[str, dict] = {}

        for i, src in enumerate(self._sources):
            original_label = src["label"]
            filepath = src["path"]
            pct = (i / total) * 100

            self._on_progress(f"Processing {original_label}...", pct)
            t0 = time.time()

            # 1. Ingest
            self._on_progress(f"  [{original_label}] Ingesting...", pct)
            df = self.ingest_file(filepath)

            # 2. Schema and Domain Detection
            self._on_progress(f"  [{original_label}] Detecting schema...", pct + 5)
            schema = detect_schema(df)
            detected_domain = detect_dataset_domain(schema)
            
            # Use detected domain if it's not "unknown_dataset", otherwise stick to original label
            label = detected_domain if detected_domain != "unknown_dataset" else original_label

            # 3. Validate
            self._on_progress(f"  [{label}] Validating...", pct + 10)
            validation = self.validate(df, label)

            # 4. Clean
            self._on_progress(f"  [{label}] Cleaning...", pct + 15)
            df_clean = self.clean(df)

            # 5. Save
            out_path = self.output_dir / f"{label}_clean.csv"
            tmp_path = out_path.with_suffix(".csv.tmp")
            df_clean.to_csv(tmp_path, index=False)
            import os; os.replace(str(tmp_path), str(out_path))

            elapsed = time.time() - t0
            results[label] = {
                "schema": schema,
                "validation": validation,
                "domain": detected_domain,
                "rows_in": len(df),
                "rows_out": len(df_clean),
                "output_path": str(out_path),
                "elapsed_sec": round(elapsed, 2),
            }

        self._on_progress("Pipeline complete.", 100.0)
        self._results = results
        return results

    def get_results(self) -> dict[str, dict]:
        """Return results from the last run."""
        return self._results

    def run_full_pipeline(self, source_dir: str | Path | None = None) -> dict[str, dict]:
        """Convenience method: auto-discover CSVs in a directory and run the pipeline."""
        if source_dir:
            self.add_sources_from_dir(source_dir, extensions=(".csv",))
        return self.run()
