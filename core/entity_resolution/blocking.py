"""
Blocking Strategies - Reduce the comparison space for entity resolution.

Each blocker generates candidate pairs that share a blocking key.
The multi_pass_blocker combines all strategies and deduplicates.

OPTIMIZED: Filters same-source pairs inside each blocker to avoid
generating millions of useless pairs. Uses vectorized operations.
"""
from __future__ import annotations

import pandas as pd
import numpy as np


def _ensure_index(df: pd.DataFrame, id_col: str = "record_id") -> pd.DataFrame:
    df = df.copy()
    if id_col not in df.columns:
        df[id_col] = [f"r_{i}" for i in range(len(df))]
    return df


def _empty_blocks() -> pd.DataFrame:
    return pd.DataFrame(columns=["id_left", "id_right", "block_key", "block_method"])


def _filter_cross_source(merged: pd.DataFrame, id_col: str) -> pd.DataFrame:
    """Vectorized filter: remove self-pairs and same-source pairs."""
    if merged.empty:
        return merged
    
    left_id = f"{id_col}_left"
    right_id = f"{id_col}_right"
    
    # Remove self-pairs
    mask = merged[left_id].values != merged[right_id].values
    
    # Remove same-source pairs (if source columns exist)
    if "_source_left" in merged.columns and "_source_right" in merged.columns:
        mask &= merged["_source_left"].values != merged["_source_right"].values
    
    return merged[mask]


def _cap_frequencies(left: pd.DataFrame, right: pd.DataFrame, cap: int = 50) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Drops block keys that appear more than `cap` times to prevent N^2 explosion."""
    l_counts = left["_bk"].value_counts()
    r_counts = right["_bk"].value_counts()
    valid_l = l_counts[l_counts <= cap].index
    valid_r = r_counts[r_counts <= cap].index
    valid_keys = valid_l.intersection(valid_r)
    return left[left["_bk"].isin(valid_keys)], right[right["_bk"].isin(valid_keys)]


def cnic_blocker(df1: pd.DataFrame, df2: pd.DataFrame, id_col: str = "record_id") -> pd.DataFrame:
    if "_cnic_normalized" not in df1.columns or "_cnic_normalized" not in df2.columns:
        return _empty_blocks()

    cols = [id_col, "_cnic_normalized"]
    if "_source" in df1.columns:
        cols = cols + ["_source"]
        
    left = df1[cols].copy()
    right = df2[cols].copy()
    
    left = left[(left["_cnic_normalized"] != "") & (left["_cnic_normalized"].notna())].copy()
    right = right[(right["_cnic_normalized"] != "") & (right["_cnic_normalized"].notna())].copy()

    if left.empty or right.empty:
        return _empty_blocks()

    left["_bk"] = left["_cnic_normalized"]
    right["_bk"] = right["_cnic_normalized"]

    left, right = _cap_frequencies(left, right, 100)

    merged = left.merge(right, on="_bk", suffixes=("_left", "_right"))
    merged = _filter_cross_source(merged, id_col)

    if merged.empty:
        return _empty_blocks()

    return pd.DataFrame({
        "id_left": merged[f"{id_col}_left"],
        "id_right": merged[f"{id_col}_right"],
        "block_key": merged["_bk"],
        "block_method": "cnic",
    })


def ntn_blocker(df1: pd.DataFrame, df2: pd.DataFrame, id_col: str = "record_id") -> pd.DataFrame:
    if "_ntn_normalized" not in df1.columns or "_ntn_normalized" not in df2.columns:
        return _empty_blocks()

    cols = [id_col, "_ntn_normalized"]
    if "_source" in df1.columns:
        cols = cols + ["_source"]
        
    left = df1[cols].copy()
    right = df2[cols].copy()
    
    left = left[(left["_ntn_normalized"] != "") & (left["_ntn_normalized"].notna()) & (left["_ntn_normalized"] != "0")].copy()
    right = right[(right["_ntn_normalized"] != "") & (right["_ntn_normalized"].notna()) & (right["_ntn_normalized"] != "0")].copy()

    if left.empty or right.empty:
        return _empty_blocks()

    left["_bk"] = left["_ntn_normalized"]
    right["_bk"] = right["_ntn_normalized"]

    left, right = _cap_frequencies(left, right, 100)

    merged = left.merge(right, on="_bk", suffixes=("_left", "_right"))
    merged = _filter_cross_source(merged, id_col)

    if merged.empty:
        return _empty_blocks()

    return pd.DataFrame({
        "id_left": merged[f"{id_col}_left"],
        "id_right": merged[f"{id_col}_right"],
        "block_key": merged["_bk"],
        "block_method": "ntn",
    })


def phone_blocker(df1: pd.DataFrame, df2: pd.DataFrame, id_col: str = "record_id") -> pd.DataFrame:
    if "_phone_normalized" not in df1.columns or "_phone_normalized" not in df2.columns:
        return _empty_blocks()

    cols = [id_col, "_phone_normalized"]
    if "_source" in df1.columns:
        cols = cols + ["_source"]
        
    left = df1[cols].copy()
    right = df2[cols].copy()
    
    left = left[(left["_phone_normalized"] != "") & (left["_phone_normalized"].notna())].copy()
    right = right[(right["_phone_normalized"] != "") & (right["_phone_normalized"].notna())].copy()

    if left.empty or right.empty:
        return _empty_blocks()

    left["_bk"] = left["_phone_normalized"]
    right["_bk"] = right["_phone_normalized"]

    left, right = _cap_frequencies(left, right, 100)

    merged = left.merge(right, on="_bk", suffixes=("_left", "_right"))
    merged = _filter_cross_source(merged, id_col)

    if merged.empty:
        return _empty_blocks()

    return pd.DataFrame({
        "id_left": merged[f"{id_col}_left"],
        "id_right": merged[f"{id_col}_right"],
        "block_key": merged["_bk"],
        "block_method": "phone",
    })


def name_city_blocker(df1: pd.DataFrame, df2: pd.DataFrame, id_col: str = "record_id") -> pd.DataFrame:
    if "_phonetic_name_normalized" not in df1.columns or "_city_normalized" not in df1.columns:
        return _empty_blocks()
    if "_phonetic_name_normalized" not in df2.columns or "_city_normalized" not in df2.columns:
        return _empty_blocks()

    cols = [id_col, "_phonetic_name_normalized", "_city_normalized"]
    if "_source" in df1.columns:
        cols = cols + ["_source"]

    left = df1[cols].copy()
    right = df2[cols].copy()

    left = left[(left["_phonetic_name_normalized"] != "") & (left["_phonetic_name_normalized"].notna()) & (left["_city_normalized"] != "") & (left["_city_normalized"].notna())].copy()
    right = right[(right["_phonetic_name_normalized"] != "") & (right["_phonetic_name_normalized"].notna()) & (right["_city_normalized"] != "") & (right["_city_normalized"].notna())].copy()

    if left.empty or right.empty:
        return _empty_blocks()

    left["_bk"] = left["_phonetic_name_normalized"] + "|" + left["_city_normalized"]
    right["_bk"] = right["_phonetic_name_normalized"] + "|" + right["_city_normalized"]

    left, right = _cap_frequencies(left, right, 50)

    merged = left.merge(right, on="_bk", suffixes=("_left", "_right"))
    merged = _filter_cross_source(merged, id_col)

    if merged.empty:
        return _empty_blocks()

    return pd.DataFrame({
        "id_left": merged[f"{id_col}_left"],
        "id_right": merged[f"{id_col}_right"],
        "block_key": merged["_bk"],
        "block_method": "name_city",
    })


def name_father_blocker(df1: pd.DataFrame, df2: pd.DataFrame, id_col: str = "record_id") -> pd.DataFrame:
    if "_name_normalized" not in df1.columns or "_father_name_normalized" not in df1.columns:
        return _empty_blocks()
    if "_name_normalized" not in df2.columns or "_father_name_normalized" not in df2.columns:
        return _empty_blocks()

    cols = [id_col, "_name_normalized", "_father_name_normalized"]
    if "_source" in df1.columns:
        cols = cols + ["_source"]

    left = df1[cols].copy()
    right = df2[cols].copy()

    left = left[(left["_name_normalized"] != "") & (left["_name_normalized"].notna()) & (left["_father_name_normalized"] != "") & (left["_father_name_normalized"].notna())].copy()
    right = right[(right["_name_normalized"] != "") & (right["_name_normalized"].notna()) & (right["_father_name_normalized"] != "") & (right["_father_name_normalized"].notna())].copy()

    if left.empty or right.empty:
        return _empty_blocks()

    left["_bk"] = left["_name_normalized"] + "|" + left["_father_name_normalized"]
    right["_bk"] = right["_name_normalized"] + "|" + right["_father_name_normalized"]

    left, right = _cap_frequencies(left, right, 50)

    merged = left.merge(right, on="_bk", suffixes=("_left", "_right"))
    merged = _filter_cross_source(merged, id_col)

    if merged.empty:
        return _empty_blocks()

    return pd.DataFrame({
        "id_left": merged[f"{id_col}_left"],
        "id_right": merged[f"{id_col}_right"],
        "block_key": merged["_bk"],
        "block_method": "name_father",
    })


def multi_pass_blocker(df1: pd.DataFrame, df2: pd.DataFrame, id_col: str = "record_id") -> pd.DataFrame:
    """Run all blocking strategies and deduplicate pairs.
    
    OPTIMIZED: Each blocker now filters same-source pairs internally,
    and deduplication uses vectorized pandas groupby.
    """
    df1 = _ensure_index(df1, id_col)
    df2 = _ensure_index(df2, id_col)

    blocks = [
        cnic_blocker(df1, df2, id_col),
        ntn_blocker(df1, df2, id_col),
        phone_blocker(df1, df2, id_col),
        name_city_blocker(df1, df2, id_col),
        name_father_blocker(df1, df2, id_col),
    ]
    combined = pd.concat(blocks, ignore_index=True)
    if combined.empty:
        return _empty_blocks()

    # Vectorized canonical pair ordering (always smaller ID on left)
    id_l = combined["id_left"].astype(str).values
    id_r = combined["id_right"].astype(str).values

    # Remove self-pairs
    mask = id_l != id_r
    if not np.any(mask):
        return _empty_blocks()

    id_l = id_l[mask]
    id_r = id_r[mask]

    swap = id_l > id_r
    c_left = np.where(swap, id_r, id_l)
    c_right = np.where(swap, id_l, id_r)

    # Fast deduplication using pandas drop_duplicates
    dedup_df = pd.DataFrame({
        "id_left": c_left,
        "id_right": c_right,
    })

    return dedup_df.drop_duplicates(ignore_index=True)
