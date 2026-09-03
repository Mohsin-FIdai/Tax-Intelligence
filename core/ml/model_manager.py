"""
Model Persistence Manager — Tax Intelligence Platform

Provides save, load, list, and delete operations for trained ML models
using joblib serialization with JSON metadata side-cars.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib

from config.settings import MODELS_DIR

logger = logging.getLogger(__name__)


class ModelManager:
    """
    Manage persistence of ML models to the ``models_store/`` directory.

    Each saved model produces two files:
        - ``<name>.joblib``   — serialized model object
        - ``<name>.meta.json`` — metadata (timestamp, metrics, version, etc.)
    """

    def __init__(self, store_dir: Optional[Path] = None) -> None:
        """
        Initialize the ModelManager.

        Parameters
        ----------
        store_dir : Path, optional
            Directory for model storage. Defaults to ``MODELS_DIR`` from config.
        """
        self._store_dir = Path(store_dir) if store_dir else MODELS_DIR
        self._store_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    #  Save                                                                #
    # ------------------------------------------------------------------ #

    def save_model(
        self,
        model: Any,
        name: str,
        metadata: Optional[Dict] = None,
    ) -> Path:
        """
        Serialize a model and its metadata to disk.

        Parameters
        ----------
        model : Any
            The trained model object (must be joblib-serializable).
        name : str
            Human-readable name used as the file stem (e.g. ``"risk_classifier_v1"``).
        metadata : dict, optional
            Extra metadata to persist (metrics, hyperparams, etc.).

        Returns
        -------
        Path
            Absolute path to the saved ``.joblib`` file.
        """
        model_path = self._store_dir / f"{name}.joblib"
        meta_path = self._store_dir / f"{name}.meta.json"

        # Serialize model
        joblib.dump(model, model_path)
        logger.info("Model saved → %s", model_path)

        # Build metadata
        meta: Dict[str, Any] = {
            "name": name,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "model_type": type(model).__name__,
            "file": str(model_path),
        }
        if metadata:
            meta["extra"] = _sanitize_metadata(metadata)

        with open(meta_path, "w", encoding="utf-8") as fp:
            json.dump(meta, fp, indent=2, default=str)
        logger.info("Metadata saved → %s", meta_path)

        return model_path

    # ------------------------------------------------------------------ #
    #  Load                                                                #
    # ------------------------------------------------------------------ #

    def load_model(self, name: str) -> Any:
        """
        Load a previously saved model from disk.

        Parameters
        ----------
        name : str
            Model name (same name used when saving).

        Returns
        -------
        Any
            The deserialized model object.

        Raises
        ------
        FileNotFoundError
            If the model file does not exist.
        """
        model_path = self._store_dir / f"{name}.joblib"
        if not model_path.exists():
            raise FileNotFoundError(
                f"Model '{name}' not found at {model_path}"
            )

        model = joblib.load(model_path)
        logger.info("Model loaded ← %s", model_path)
        return model

    # ------------------------------------------------------------------ #
    #  Load metadata                                                       #
    # ------------------------------------------------------------------ #

    def load_metadata(self, name: str) -> Dict:
        """
        Load the metadata sidecar for a saved model.

        Parameters
        ----------
        name : str
            Model name.

        Returns
        -------
        dict
            Metadata dictionary.

        Raises
        ------
        FileNotFoundError
            If the metadata file does not exist.
        """
        meta_path = self._store_dir / f"{name}.meta.json"
        if not meta_path.exists():
            raise FileNotFoundError(
                f"Metadata for model '{name}' not found at {meta_path}"
            )

        with open(meta_path, "r", encoding="utf-8") as fp:
            return json.load(fp)

    # ------------------------------------------------------------------ #
    #  List                                                                #
    # ------------------------------------------------------------------ #

    def list_models(self) -> List[Dict]:
        """
        List all saved models with their metadata.

        Returns
        -------
        list of dict
            Each dict contains at minimum ``name`` and ``saved_at``.
            If a metadata file is present, additional fields are included.
        """
        models: List[Dict] = []
        for joblib_file in sorted(self._store_dir.glob("*.joblib")):
            name = joblib_file.stem
            meta_path = self._store_dir / f"{name}.meta.json"

            entry: Dict[str, Any] = {
                "name": name,
                "file": str(joblib_file),
                "size_bytes": joblib_file.stat().st_size,
            }

            if meta_path.exists():
                try:
                    with open(meta_path, "r", encoding="utf-8") as fp:
                        meta = json.load(fp)
                    entry.update(meta)
                except (json.JSONDecodeError, OSError) as exc:
                    logger.warning("Failed to read metadata for '%s': %s", name, exc)

            models.append(entry)

        logger.info("Found %d saved models in %s", len(models), self._store_dir)
        return models

    # ------------------------------------------------------------------ #
    #  Delete                                                              #
    # ------------------------------------------------------------------ #

    def delete_model(self, name: str) -> bool:
        """
        Delete a saved model and its metadata from disk.

        Parameters
        ----------
        name : str
            Model name.

        Returns
        -------
        bool
            True if at least one file was deleted.
        """
        deleted = False
        for suffix in [".joblib", ".meta.json"]:
            path = self._store_dir / f"{name}{suffix}"
            if path.exists():
                path.unlink()
                deleted = True
                logger.info("Deleted %s", path)

        if not deleted:
            logger.warning("No files found for model '%s'", name)
        return deleted

    # ------------------------------------------------------------------ #
    #  Existence check                                                     #
    # ------------------------------------------------------------------ #

    def model_exists(self, name: str) -> bool:
        """
        Check whether a model with the given name has been saved.

        Parameters
        ----------
        name : str
            Model name.

        Returns
        -------
        bool
        """
        return (self._store_dir / f"{name}.joblib").exists()


# ────────────────────────────────────────────────────────────────────── #
#  Module-level utility                                                  #
# ────────────────────────────────────────────────────────────────────── #


def _sanitize_metadata(meta: Dict) -> Dict:
    """
    Sanitize a metadata dict so it is JSON-serializable.

    Converts numpy types, Paths, etc. to native Python types.

    Parameters
    ----------
    meta : dict
        Raw metadata dictionary.

    Returns
    -------
    dict
        Cleaned dictionary safe for ``json.dump``.
    """
    import numpy as np

    clean: Dict = {}
    for key, value in meta.items():
        if isinstance(value, (np.integer,)):
            clean[key] = int(value)
        elif isinstance(value, (np.floating,)):
            clean[key] = float(value)
        elif isinstance(value, np.ndarray):
            clean[key] = value.tolist()
        elif isinstance(value, Path):
            clean[key] = str(value)
        elif isinstance(value, dict):
            clean[key] = _sanitize_metadata(value)
        elif isinstance(value, (list, tuple)):
            clean[key] = [
                _sanitize_metadata(v) if isinstance(v, dict) else v
                for v in value
            ]
        else:
            clean[key] = value
    return clean
