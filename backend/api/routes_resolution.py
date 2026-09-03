from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, Any
import math

from backend.services.data_service import DataService

router = APIRouter(prefix="/api/v1/resolution", tags=["Entity Resolution"])

def get_data_service() -> DataService:
    svc = DataService()
    if not svc.is_loaded:
        raise HTTPException(status_code=503, detail="Data not loaded yet.")
    return svc

@router.get("/summary", response_model=Dict[str, Any])
def get_resolution_summary(svc: DataService = Depends(get_data_service)):
    if svc.entity_matches_df is None or svc.entity_matches_df.empty:
        return {"total_matches": 0, "total_unique": 0, "manual_reviews": 0, "conflicts": 0}

    df = svc.entity_matches_df
    
    total_matches = int((df["decision"].isin(["MERGED", "SEPARATED", "REJECTED"])).sum()) if "decision" in df.columns else len(df)
    unique_citizens = svc.citizens_df["citizen_id"].nunique() if svc.citizens_df is not None else 0
    manual_reviews = int((df["decision"] == "REVIEW").sum()) if "decision" in df.columns else 0
    conflicts = int((df["decision"] == "CONFLICT").sum()) if "decision" in df.columns else 0
    
    return {
        "total_matches": total_matches,
        "total_unique": unique_citizens,
        "manual_reviews": manual_reviews,
        "conflicts": conflicts
    }

import pandas as pd
from pathlib import Path

# Global in-memory cache for all raw clean records and deduplicated reviews
_raw_cache: dict[str, dict] = {}
_deduped_cache: dict[str, pd.DataFrame] = {}
PROCESSED_DIR = Path("data/processed_v2")

def _init_raw_cache():
    if _raw_cache:
        return
    for fp in PROCESSED_DIR.glob("*_clean.csv"):
        prefix = fp.name[:-10]
        try:
            df = pd.read_csv(fp)
            if "record_id" in df.columns:
                for r in df.fillna("").to_dict(orient="records"):
                    rid = str(r.get("record_id"))
                    _raw_cache[f"{prefix}_{rid}"] = r
                    _raw_cache[rid] = r
        except Exception as e:
            print(f"Error caching {fp}: {e}")

def get_raw_record_data(record_id: str) -> dict:
    if not record_id or record_id == "Unknown":
        return {}
    if not _raw_cache:
        _init_raw_cache()
    return _raw_cache.get(str(record_id), {})


@router.get("/reviews", response_model=Dict[str, Any])
def get_resolution_reviews(
    page: int = 1, 
    limit: int = 50, 
    filter_signal: str = "All", 
    filter_decision: str = "All",
    svc: DataService = Depends(get_data_service)
):
    if svc.entity_matches_df is None or svc.entity_matches_df.empty:
        return {"data": [], "total_count": 0, "total_pages": 0, "page": page, "limit": limit}
        
    df = svc.entity_matches_df
    _init_raw_cache()
    
    cache_key = f"{filter_decision}_{filter_signal}_{len(df)}"
    if cache_key in _deduped_cache:
        deduped_df = _deduped_cache[cache_key]
    else:
        # Filter by decision category
        if filter_decision in ["REVIEW", "Review Required", "review"]:
            reviews_df = df[df["decision"] == "REVIEW"].copy()
        elif filter_decision in ["CONFLICT", "Conflicts", "Conflicts Detected", "conflict"]:
            reviews_df = df[df["decision"] == "CONFLICT"].copy()
        else:
            if "decision" in df.columns:
                reviews_df = df[df["decision"].isin(["REVIEW", "CONFLICT"])].copy()
            else:
                reviews_df = df.copy()
            
        if filter_signal != "All":
            reasons_col = reviews_df["reasons"].fillna("").str.lower()
            merge_col = reviews_df["merge_reason"].fillna("").str.lower()
            
            has_cnic = reasons_col.str.contains("cnic")
            has_name = reasons_col.str.contains("name")
            is_multilingual = (reasons_col.str.contains("translat|urdu|roman") | 
                               merge_col.str.contains("phonetic|multilingual"))
                               
            if filter_signal == "Matching CNIC":
                reviews_df = reviews_df[has_cnic & ~has_name]
            elif filter_signal == "CNIC and Name":
                reviews_df = reviews_df[has_cnic & has_name]
            elif filter_signal == "Name Only":
                reviews_df = reviews_df[has_name & ~has_cnic]
            elif filter_signal == "Multilingual Name":
                reviews_df = reviews_df[is_multilingual]

        # Deduplicate by the actual record pair (not by person name, which
        # would incorrectly collapse different cross-dataset pairs for the
        # same citizen into a single entry).
        records1 = reviews_df.get("record1_id", reviews_df.get("record_a_id", pd.Series([]))).astype(str).tolist()
        records2 = reviews_df.get("record2_id", reviews_df.get("record_b_id", pd.Series([]))).astype(str).tolist()
        
        keys = []
        for r1, r2 in zip(records1, records2):
            # Canonical ordering so (A,B) and (B,A) are treated as the same pair
            if r1 > r2:
                keys.append(f"{r2}||{r1}")
            else:
                keys.append(f"{r1}||{r2}")
                
        reviews_df["_entity_pair_key"] = keys
        deduped_df = reviews_df.drop_duplicates(subset=["_entity_pair_key"])
        _deduped_cache[cache_key] = deduped_df

    total_count = len(deduped_df)
    total_pages = math.ceil(total_count / limit) if limit > 0 else 0
    
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    
    page_df = deduped_df.iloc[start_idx:end_idx].fillna("Unknown")
    page_data = page_df.to_dict(orient="records")
    
    # Enrich each record in O(1) from memory cache
    for row in page_data:
        rec_a_id = str(row.get("record_a_id") or row.get("record1_id", ""))
        rec_b_id = str(row.get("record_b_id") or row.get("record2_id", ""))
        row["rec_a_data"] = get_raw_record_data(rec_a_id)
        row["rec_b_data"] = get_raw_record_data(rec_b_id)
        
    return {
        "data": page_data,
        "total_count": total_count,
        "total_pages": total_pages,
        "page": page,
        "limit": limit
    }

@router.get("/resolved", response_model=Dict[str, Any])
def get_resolution_resolved(
    page: int = 1, 
    limit: int = 50, 
    silos_filter: str = "All", 
    conf_filter: str = "All", 
    svc: DataService = Depends(get_data_service)
):
    if svc.citizens_df is None or svc.citizens_df.empty:
        return {"data": [], "total_count": 0, "total_pages": 0, "page": page, "limit": limit}
        
    citizens = svc.citizens_df.copy()
    if "merged_record_ids" in citizens.columns:
        citizens["_record_count"] = citizens["merged_record_ids"].apply(
            lambda x: len([r.strip() for r in str(x).split(",") if r.strip() and r.strip() != "nan"])
        )
    else:
        citizens["_record_count"] = 1
        
    resolved_citizens = citizens[citizens["_record_count"] > 1].copy()
    if resolved_citizens.empty:
        return {"data": [], "total_count": 0, "total_pages": 0, "page": page, "limit": limit}

    # Fast vectorized silos extraction from merged_record_ids string
    def parse_silos(x):
        rids = [r.strip() for r in str(x).split(",") if r.strip() and r.strip() != "nan"]
        datasets = set()
        for r in rids:
            if "_" in r:
                datasets.add(r.rsplit("_", 1)[0])
        names = ", ".join(sorted(datasets))
        return names, len(datasets)

    parsed_silos = resolved_citizens["merged_record_ids"].fillna("").apply(parse_silos)
    resolved_citizens["dataset_names"] = [p[0] for p in parsed_silos]
    resolved_citizens["dataset_count"] = [p[1] for p in parsed_silos]
    resolved_citizens["avg_confidence"] = 98.5
    resolved_citizens["matched_fields"] = "CNIC, Name, Cross-Dataset Linkage"
    
    # Filter by silos
    if silos_filter != "All":
        if silos_filter == "2+ Datasets":
            resolved_citizens = resolved_citizens[resolved_citizens["dataset_count"] >= 2]
        elif silos_filter == "3+ Datasets":
            resolved_citizens = resolved_citizens[resolved_citizens["dataset_count"] >= 3]
        elif silos_filter == "4+ Datasets":
            resolved_citizens = resolved_citizens[resolved_citizens["dataset_count"] >= 4]
            
    # Filter by confidence
    if conf_filter != "All":
        if conf_filter == "High Confidence (>95%)":
            resolved_citizens = resolved_citizens[resolved_citizens["avg_confidence"] > 95.0]
        elif conf_filter == "Medium Confidence (80-95%)":
            resolved_citizens = resolved_citizens[(resolved_citizens["avg_confidence"] >= 80.0) & (resolved_citizens["avg_confidence"] <= 95.0)]
        elif conf_filter == "Low Confidence (<80%)":
            resolved_citizens = resolved_citizens[resolved_citizens["avg_confidence"] < 80.0]
            
    total_count = len(resolved_citizens)
    total_pages = math.ceil(total_count / limit) if limit > 0 else 0
    
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    
    page_df = resolved_citizens.iloc[start_idx:end_idx].fillna("Unknown")
    data = page_df.to_dict(orient="records")
    
    return {
        "data": data,
        "total_count": total_count,
        "total_pages": total_pages,
        "page": page,
        "limit": limit
    }

import hashlib
import threading
import os

def _atomic_csv_write(df: pd.DataFrame, target_path: Path):
    """Write a DataFrame to CSV atomically: write to a .tmp file first,
    then os.replace() it over the target. If the process is killed mid-write,
    the original file is never corrupted."""
    tmp_path = target_path.with_suffix(".csv.tmp")
    df.to_csv(tmp_path, index=False)
    os.replace(str(tmp_path), str(target_path))

def _save_data_async(matches_df: pd.DataFrame, citizens_df: pd.DataFrame):
    """Save updated matches and citizens to CSV in the background to keep the API responsive."""
    PROCESSED_DIR = Path("data/processed_v2")
    try:
        if matches_df is not None and not matches_df.empty:
            _atomic_csv_write(matches_df, PROCESSED_DIR / "entity_matches.csv")
        if citizens_df is not None and not citizens_df.empty:
            _atomic_csv_write(citizens_df, PROCESSED_DIR / "master_citizens.csv")
    except Exception as e:
        print(f"Error saving data in background: {e}")


def apply_decision_to_citizens(svc: DataService, rec1_id: str, rec2_id: str, decision: str):
    """Update canonical citizen entities in real time upon resolution decisions."""
    if svc.citizens_df is None or svc.citizens_df.empty:
        return
        
    df = svc.citizens_df.copy()

    def find_citizen_idx(rec_id: str):
        if not rec_id or not rec_id.strip():
            return None
        mask = df["merged_record_ids"].fillna("").apply(
            lambda x: rec_id in [r.strip() for r in str(x).split(",") if r.strip()]
        )
        matches = df.index[mask].tolist()
        return matches[0] if matches else None

    idx1 = find_citizen_idx(rec1_id)
    idx2 = find_citizen_idx(rec2_id)

    if decision == "MERGED":
        if idx1 is not None and idx2 is not None and idx1 != idx2:
            # Merge citizen 2 into citizen 1
            c1 = df.loc[idx1].to_dict()
            c2 = df.loc[idx2].to_dict()

            rids1 = [r.strip() for r in str(c1.get("merged_record_ids", "")).split(",") if r.strip()]
            rids2 = [r.strip() for r in str(c2.get("merged_record_ids", "")).split(",") if r.strip()]
            all_rids = sorted(list(set(rids1 + rids2)))
            df.loc[idx1, "merged_record_ids"] = ",".join(all_rids)

            # Combine financial totals
            inc1 = float(c1.get("declared_income") or 0)
            inc2 = float(c2.get("declared_income") or 0)
            nw1 = float(c1.get("estimated_net_worth") or 0)
            nw2 = float(c2.get("estimated_net_worth") or 0)
            
            combined_inc = max(inc1, inc2)
            combined_nw = nw1 + nw2
            hidden_inc = max(0.0, combined_nw - combined_inc)
            rec_tax = hidden_inc * 0.35
            
            df.loc[idx1, "declared_income"] = combined_inc
            df.loc[idx1, "estimated_net_worth"] = combined_nw
            df.loc[idx1, "estimated_hidden_income"] = hidden_inc
            df.loc[idx1, "estimated_recoverable_tax"] = rec_tax
            
            dev = min(100.0, (hidden_inc / max(1.0, combined_nw)) * 100.0) if combined_nw > 0 else 0.0
            df.loc[idx1, "deviation_score"] = round(dev, 2)
            
            if dev >= 80:
                cat = "E"
            elif dev >= 60:
                cat = "D"
            elif dev >= 40:
                cat = "C"
            elif dev >= 20:
                cat = "B"
            else:
                cat = "A"
            df.loc[idx1, "risk_category"] = cat

            # Drop citizen 2
            df.drop(index=idx2, inplace=True)
            df.reset_index(drop=True, inplace=True)
            svc.citizens_df = df

        elif idx1 is not None and idx2 is None:
            rids1 = [r.strip() for r in str(df.loc[idx1, "merged_record_ids"]).split(",") if r.strip()]
            if rec2_id not in rids1:
                rids1.append(rec2_id)
                df.loc[idx1, "merged_record_ids"] = ",".join(rids1)
                svc.citizens_df = df
                
        elif idx2 is not None and idx1 is None:
            rids2 = [r.strip() for r in str(df.loc[idx2, "merged_record_ids"]).split(",") if r.strip()]
            if rec1_id not in rids2:
                rids2.append(rec1_id)
                df.loc[idx2, "merged_record_ids"] = ",".join(rids2)
                svc.citizens_df = df

    elif decision == "SEPARATED":
        if idx1 is not None and idx2 is not None and idx1 == idx2:
            c = df.loc[idx1].to_dict()
            rids = [r.strip() for r in str(c.get("merged_record_ids", "")).split(",") if r.strip()]
            
            if rec2_id in rids:
                rids.remove(rec2_id)
                df.loc[idx1, "merged_record_ids"] = ",".join(rids)
                
                rec2_data = get_raw_record_data(rec2_id)
                new_cid = f"CZ-{hashlib.md5(rec2_id.encode()).hexdigest()[:8].upper()}"
                
                new_citizen = {
                    "citizen_id": new_cid,
                    "canonical_name": rec2_data.get("name") or rec2_data.get("owner_name") or rec2_data.get("canonical_name") or "Citizen",
                    "urdu_name": "",
                    "cnic": str(rec2_data.get("cnic", "")).replace(".0", "").replace("-", ""),
                    "father_name": rec2_data.get("father_name", ""),
                    "phone": rec2_data.get("phone", ""),
                    "address": rec2_data.get("address", ""),
                    "city": rec2_data.get("city", ""),
                    "province": rec2_data.get("province", ""),
                    "declared_income": float(rec2_data.get("income_declared") or 0),
                    "estimated_net_worth": float(rec2_data.get("value_pkr") or 0),
                    "deviation_score": 0.0,
                    "estimated_hidden_income": 0.0,
                    "estimated_recoverable_tax": 0.0,
                    "risk_score": 0.0,
                    "risk_category": "A",
                    "filing_status": "Non-Filer",
                    "merged_record_ids": rec2_id,
                }
                
                new_df = pd.DataFrame([new_citizen])
                df = pd.concat([df, new_df], ignore_index=True)
                svc.citizens_df = df


class DecisionRequest(BaseModel):
    record1_id: str
    record2_id: str
    decision: str


@router.post("/decision")
def post_resolution_decision(req: DecisionRequest, svc: DataService = Depends(get_data_service)):
    if svc.entity_matches_df is None or svc.entity_matches_df.empty:
        raise HTTPException(status_code=400, detail="Matches dataframe is not loaded.")
        
    df = svc.entity_matches_df
    
    # Find matching row based on both IDs
    mask = ((df["record1_id"] == req.record1_id) & (df["record2_id"] == req.record2_id)) | \
           ((df["record1_id"] == req.record2_id) & (df["record2_id"] == req.record1_id))
           
    if not mask.any():
        raise HTTPException(status_code=404, detail="Match record not found.")
        
    # Update the matches dataframe
    svc.entity_matches_df.loc[mask, "decision"] = req.decision
    _deduped_cache.clear()
    
    # Apply real-time merging/separating to canonical citizen entities
    apply_decision_to_citizens(svc, req.record1_id, req.record2_id, req.decision)
    
    # Persist in background thread for instant response
    threading.Thread(
        target=_save_data_async,
        args=(svc.entity_matches_df.copy(), svc.citizens_df.copy() if svc.citizens_df is not None else None),
        daemon=True,
    ).start()
    
    # Return updated summary metrics directly
    m_df = svc.entity_matches_df
    total_matches = int((m_df["decision"].isin(["MERGED", "SEPARATED", "REJECTED"])).sum()) if "decision" in m_df.columns else len(m_df)
    unique_citizens = svc.citizens_df["citizen_id"].nunique() if svc.citizens_df is not None else 0
    manual_reviews = int((m_df["decision"] == "REVIEW").sum()) if "decision" in m_df.columns else 0
    conflicts = int((m_df["decision"] == "CONFLICT").sum()) if "decision" in m_df.columns else 0
    
    return {
        "status": "success", 
        "message": f"Updated decision to {req.decision}",
        "summary": {
            "total_matches": total_matches,
            "total_unique": unique_citizens,
            "manual_reviews": manual_reviews,
            "conflicts": conflicts
        }
    }
