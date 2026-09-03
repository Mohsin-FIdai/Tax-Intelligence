"""
Entity Resolver — Merges records across datasets into unified citizen profiles.
"""
from __future__ import annotations

import sys
import uuid
import re
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config.settings import PROCESSED_DIR
from core.entity_resolution.name_normalizer import normalize_name, parse_name
from core.entity_resolution.confidence_scorer import score_match, explain_match


def normalize_cnic(val) -> str:
    """Normalize CNIC to 13 digits. Returns '' if invalid."""
    if pd.isna(val):
        return ""
    val = str(val).strip()
    if val.lower() in ("", "nan", "none", "null", "unknown", "n/a"):
        return ""
    val = re.sub(r"\D", "", val)
    # Pakistani CNIC is exactly 13 digits
    if len(val) != 13:
        return ""
    return val


def normalize_phone(val) -> str:
    """Normalize phone to canonical 11-digit 03xx format. Returns '' if invalid."""
    if pd.isna(val):
        return ""
    val = str(val).strip()
    if val.lower() in ("", "nan", "none", "null", "unknown", "n/a"):
        return ""
    val = re.sub(r"\D", "", val)
    # Handle +92 / 0092 prefix -> 0
    if val.startswith("92") and len(val) == 12:
        val = "0" + val[2:]
    elif val.startswith("92") and len(val) > 12:
        val = "0" + val[2:]
    # Handle missing leading zero (10-digit mobile)
    if len(val) == 10 and val[0] == "3":
        val = "0" + val
    # Validate: Pakistani mobile is 03xx-xxxxxxx = 11 digits
    if len(val) != 11 or not val.startswith("03"):
        return ""
    return val


def normalize_city(val) -> str:
    if pd.isna(val):
        return ''
    val = str(val).strip().lower()
    if val in ('', 'nan', 'none', 'null', 'unknown', 'n/a', 'not available', 'not applicable'):
        return ''
    return val


def normalize_address(val) -> str:
    if pd.isna(val):
        return ''
    val = str(val).strip().lower()
    if val in ('', 'nan', 'none', 'null', 'unknown', 'n/a', 'unknown address', 'not available', 'not applicable'):
        return ''
    val = re.sub(r'\s+', ' ', val)
    return val


def normalize_record_for_matching(record: dict) -> dict:
    """Create a normalized record with canonical fields for matching.
    
    IMPORTANT: This function maps from various source column names to
    standard normalized fields. The datasets use 'canonical_name' as the
    name column, NOT 'name'.
    """
    res = {}
    res['record_id'] = str(record.get('record_id', record.get('citizen_id', '')))
    res['_source'] = record.get('_source', '')

    res['_cnic_normalized'] = normalize_cnic(record.get('cnic', ''))

    # Phone: check multiple possible column names
    phone = record.get('phone', record.get('phone_number', ''))
    res['_phone_normalized'] = normalize_phone(phone)

    # Name: datasets use 'canonical_name', not 'name'
    # Check all possible name columns in order of priority
    name = record.get('canonical_name',
           record.get('name',
           record.get('owner_name',
           record.get('account_holder',
           record.get('traveler_name', '')))))
    parsed = parse_name(str(name)) if pd.notna(name) and str(name).strip() not in ('', 'nan', 'None') else None
    res['_name_normalized'] = parsed.canonical if parsed else ''
    res['_phonetic_name_normalized'] = parsed.phonetic if parsed else ''

    # Father name
    fname = record.get('father_name', '')
    parsed_fname = parse_name(str(fname)) if pd.notna(fname) and str(fname).strip() not in ('', 'nan', 'None') else None
    res['_father_name_normalized'] = parsed_fname.canonical if parsed_fname else ''

    res['_city_normalized'] = normalize_city(record.get('city', ''))
    res['_address_normalized'] = normalize_address(record.get('address', record.get('registered_office_address', '')))

    ntn = record.get('ntn', '')
    if pd.isna(ntn) or str(ntn).strip().lower() in ('', 'nan', 'none', 'null'):
        res['_ntn_normalized'] = ''
    else:
        res['_ntn_normalized'] = re.sub(r'\D', '', str(ntn).strip())

    # Merge original record with normalized fields
    return {**record, **res}


class EntityResolver:
    """Multi-pass entity resolution engine.

    Strategy
    --------
    1. **Deterministic** — exact CNIC match across datasets.
    2. **Strong probabilistic** — CNIC + name or phone + name.
    3. **Fuzzy probabilistic** — name similarity + city/father.
    4. **Graph-based** — connected-component clustering with conflict guards.

    The output is a master citizen table with a unique ``citizen_id`` per
    resolved entity together with a match-log table.
    """

    def __init__(self):
        self.match_log: list[dict] = []

    # ────────────────────────────────────────────────────────────────
    # Helpers
    # ────────────────────────────────────────────────────────────────

    @staticmethod
    def _standardise(df: pd.DataFrame, source_label: str) -> pd.DataFrame:
        """Add source label and normalise key columns."""
        df = df.copy()
        df["_source"] = source_label

        # Ensure a record_id
        if "record_id" not in df.columns and "citizen_id" not in df.columns:
            df["record_id"] = [f"{source_label}_{i}" for i in range(len(df))]
        elif "citizen_id" in df.columns and "record_id" not in df.columns:
            df["record_id"] = df["citizen_id"]

        # Ensure global uniqueness across datasets
        df["record_id"] = df["record_id"].apply(
            lambda x: f"{source_label}_{x}" if not str(x).startswith(f"{source_label}_") else str(x)
        )

        name_col = None
        for cand in ['canonical_name', 'name', 'owner_name', 'account_holder', 'traveler_name']:
            if cand in df.columns:
                name_col = cand
                break

        if name_col:
            unique_names = [n for n in df[name_col].dropna().unique() if str(n).strip() not in ('', 'nan', 'None')]
            name_cache = {n: parse_name(str(n)) for n in unique_names}
            parsed_s = df[name_col].map(lambda x: name_cache.get(x) if pd.notna(x) else None)
            df["_name_normalized"] = parsed_s.apply(lambda p: p.canonical if p else "")
            df["_phonetic_name_normalized"] = parsed_s.apply(lambda p: p.phonetic if p else "")
        else:
            df["_name_normalized"] = ""
            df["_phonetic_name_normalized"] = ""

        if "father_name" in df.columns:
            unique_fnames = [f for f in df["father_name"].dropna().unique() if str(f).strip() not in ('', 'nan', 'None')]
            fname_cache = {f: parse_name(str(f)) for f in unique_fnames}
            parsed_f = df["father_name"].map(lambda x: fname_cache.get(x) if pd.notna(x) else None)
            df["_father_name_normalized"] = parsed_f.apply(lambda p: p.canonical if p else "")
        else:
            df["_father_name_normalized"] = ""

        if "cnic" in df.columns:
            df["_cnic_normalized"] = df["cnic"].apply(normalize_cnic)
        else:
            df["_cnic_normalized"] = ""

        phone_col = "phone" if "phone" in df.columns else ("phone_number" if "phone_number" in df.columns else None)
        if phone_col:
            df["_phone_normalized"] = df[phone_col].apply(normalize_phone)
        else:
            df["_phone_normalized"] = ""

        if "city" in df.columns:
            df["_city_normalized"] = df["city"].apply(normalize_city)
        else:
            df["_city_normalized"] = ""

        addr_col = "address" if "address" in df.columns else ("registered_office_address" if "registered_office_address" in df.columns else None)
        if addr_col:
            df["_address_normalized"] = df[addr_col].apply(normalize_address)
        else:
            df["_address_normalized"] = ""

        if "ntn" in df.columns:
            df["_ntn_normalized"] = df["ntn"].fillna("").astype(str).str.replace(r"\D", "", regex=True)
            df.loc[df["_ntn_normalized"].isin(["", "nan", "none"]), "_ntn_normalized"] = ""
        else:
            df["_ntn_normalized"] = ""

        return df

    def _merge_cluster(self, records: list[dict]) -> dict:
        """Merge a cluster of matched records into a single citizen profile."""
        citizen_id = f"CZ-{uuid.uuid4().hex[:8].upper()}"

        # Sort records deterministically: tax records first, then alphabetically by source
        source_priority = {"tax_records": 0, "mobile_records": 1, "property_records": 2,
                          "vehicle_records": 3, "business_records": 4, "utility_records": 5,
                          "travel_records": 6}
        records = sorted(records, key=lambda r: (
            source_priority.get(r.get("_source", ""), 99),
            str(r.get("record_id", ""))
        ))

        def _best(key: str) -> str:
            vals = [str(r[key]).strip() for r in records if key in r and pd.notna(r[key]) and str(r[key]).strip() not in ('', 'nan', 'None')]
            if not vals:
                return ""
            # Return most frequent
            return max(set(vals), key=vals.count)

        name_cols = ["canonical_name", "name", "owner_name", "account_holder", "traveler_name"]
        def _best_name() -> str:
            vals = []
            for r in records:
                for c in name_cols:
                    if c in r and pd.notna(r[c]) and str(r[c]).strip() not in ('', 'nan', 'None'):
                        vals.append(str(r[c]).strip())
                        break
            if not vals:
                # Fallback to normalized if all else fails
                return _best("_name_normalized")
            return max(set(vals), key=vals.count)

        # Extract native Urdu script name if present in any merged record
        urdu_pattern = re.compile(r'[\u0600-\u06ff]')
        urdu_name = ""
        for r in records:
            for c in ["name", "canonical_name", "owner_name", "account_holder", "traveler_name"]:
                val = str(r.get(c, "")).strip()
                if urdu_pattern.search(val) and val.lower() not in ('nan', 'none', ''):
                    urdu_name = val
                    break
            if urdu_name:
                break

        # Extract English name candidates
        english_names = []
        for r in records:
            for c in ["canonical_name", "name", "owner_name", "account_holder", "traveler_name"]:
                val = str(r.get(c, "")).strip()
                if val and not urdu_pattern.search(val) and val.lower() not in ('nan', 'none', ''):
                    english_names.append(val)
                    break

        if english_names:
            best_eng_name = max(set(english_names), key=english_names.count)
        else:
            best_eng_name = _best("_name_normalized")
            if not best_eng_name and urdu_name:
                from core.entity_resolution.name_normalizer import parse_name
                best_eng_name = parse_name(urdu_name).canonical

        if urdu_name and best_eng_name:
            if urdu_name not in best_eng_name:
                full_canonical_name = f"{best_eng_name} ({urdu_name})"
            else:
                full_canonical_name = best_eng_name
        elif best_eng_name:
            full_canonical_name = best_eng_name
        elif urdu_name:
            full_canonical_name = urdu_name
        else:
            full_canonical_name = citizen_id

        # Extract father name
        urdu_fname = ""
        for r in records:
            for c in ["father_name", "father"]:
                val = str(r.get(c, "")).strip()
                if urdu_pattern.search(val) and val.lower() not in ('nan', 'none', ''):
                    urdu_fname = val
                    break
            if urdu_fname:
                break

        eng_fnames = [str(r.get("father_name", "")).strip() for r in records if "father_name" in r and not urdu_pattern.search(str(r.get("father_name", ""))) and str(r.get("father_name", "")).strip() not in ('', 'nan', 'None')]
        if eng_fnames:
            best_eng_fname = max(set(eng_fnames), key=eng_fnames.count)
        else:
            best_eng_fname = _best("_father_name_normalized")
            if not best_eng_fname and urdu_fname:
                from core.entity_resolution.name_normalizer import parse_name
                best_eng_fname = parse_name(urdu_fname).canonical

        if urdu_fname and best_eng_fname:
            if urdu_fname not in best_eng_fname:
                full_father_name = f"{best_eng_fname} ({urdu_fname})"
            else:
                full_father_name = best_eng_fname
        elif best_eng_fname:
            full_father_name = best_eng_fname
        elif urdu_fname:
            full_father_name = urdu_fname
        else:
            full_father_name = ""

        # Collect distinct values deterministically (preserving sorted order)
        cnics = []
        for r in records:
            c = str(r.get("_cnic_normalized", ""))
            if c and c not in cnics:
                cnics.append(c)

        sources = []
        record_ids = []
        for r in records:
            s = r.get("_source", "")
            if s and s not in sources:
                sources.append(s)
            rid = r.get("record_id", "")
            if rid:
                record_ids.append(str(rid))

        return {
            "citizen_id": citizen_id,
            "canonical_name": full_canonical_name,
            "urdu_name": urdu_name,
            "cnic": cnics[0] if cnics else "",
            "ntn": _best("ntn"),
            "father_name": full_father_name,
            "city": _best("_city_normalized") or _best("city"),
            "province": _best("province"),
            "phone": _best("_phone_normalized") or _best("phone"),
            "address": _best("_address_normalized") or _best("address"),
            "filing_status": (
                "Filer" if any("Federal Board of Revenue" in str(r.get("_source", "")) for r in records)
                else (
                    "Filer" if str(_best("return_status")).lower() in ("filed", "filer", "active", "yes")
                    else (
                        "Filer (Nil)" if str(_best("return_status")).lower() in ("nil return", "nil")
                        else "Non-Filer"
                    )
                )
            ),
            "declared_income": _best("declared_income") or _best("income_declared") or _best("income") or _best("annual_income") or "",
            "tax_paid": _best("tax_paid") or _best("tax") or _best("tax_declared") or "",
            "num_sources": len(sources),
            "sources": ",".join(sources),
            "merged_record_ids": ",".join(record_ids),
        }

    # ────────────────────────────────────────────────────────────────
    # Main resolver
    # ────────────────────────────────────────────────────────────────

    def resolve(self, datasets: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Resolve entities across multiple datasets."""
        import networkx as nx
        from core.entity_resolution.blocking import multi_pass_blocker

        all_records: list[dict] = []
        record_map = {}
        for label, df in datasets.items():
            std = self._standardise(df, label)
            recs = std.to_dict("records")
            for rec in recs:
                rid = str(rec["record_id"])
                rec["record_id"] = rid
                all_records.append(rec)
                record_map[rid] = rec

        print(f"  Total records: {len(all_records):,}")
        print(f"  Record map size: {len(record_map):,}")

        # ── Candidate Generation (Blocking) ──────────────────────
        df_all = pd.DataFrame(all_records)

        # Blocking now filters same-source pairs internally
        blocked_pairs_df = multi_pass_blocker(df_all, df_all, id_col="record_id")

        # Pairs are already cross-source filtered by optimized blockers.
        # IDs are guaranteed to exist in record_map because df_all was built from it.
        id_lefts = blocked_pairs_df["id_left"].values
        id_rights = blocked_pairs_df["id_right"].values
        candidate_pairs = list(zip(id_lefts.astype(str), id_rights.astype(str)))

        print(f"  Blocked cross-source pairs: {len(blocked_pairs_df):,}")
        print(f"  Valid candidate pairs: {len(candidate_pairs):,}")

        # ── Similarity Scoring ───────────────────────────────────
        from core.entity_resolution.match_model import RuleBasedMatchModel
        from joblib import Parallel, delayed

        G = nx.Graph()
        for rid in record_map:
            G.add_node(rid)

        def _score_chunk(chunk):
            model = RuleBasedMatchModel()
            chunk_log = []
            chunk_edges = []
            for rid1, rid2 in chunk:
                rec1 = record_map[rid1]
                rec2 = record_map[rid2]
                result = model.predict(rec1, rec2)
                chunk_log.append({
                    "record1_id": rid1,
                    "record2_id": rid2,
                    "source_domain_a": rec1.get("_source", ""),
                    "source_domain_b": rec2.get("_source", ""),
                    "confidence": result["confidence"],
                    "decision": result["decision"],
                    "reasons": str([r["field"] for r in result["reasons"]]),
                    "risk_level": result["risk_level"],
                    "merge_reason": result["merge_reason"],
                })
                if result["decision"] == "MERGED":
                    chunk_edges.append((rid1, rid2))
            return chunk_log, chunk_edges

        print(f"  Scoring {len(candidate_pairs):,} pairs (single thread)...")
        chunk_log, chunk_edges = _score_chunk(candidate_pairs)
        self.match_log.extend(chunk_log)
        G.add_edges_from(chunk_edges)

        # ── Entity Clustering with conflict safeguards ───────────
        raw_clusters = list(nx.connected_components(G))

        # Sub-cluster by CNIC to prevent transitive false merges
        final_clusters = []
        for cluster in raw_clusters:
            if len(cluster) <= 2:
                final_clusters.append(cluster)
                continue

            # Group by CNIC within the cluster
            cnic_groups = {}
            no_cnic = []
            for rid in cluster:
                cnic = record_map[rid].get("_cnic_normalized", "")
                if cnic:
                    if cnic not in cnic_groups:
                        cnic_groups[cnic] = []
                    cnic_groups[cnic].append(rid)
                else:
                    no_cnic.append(rid)

            if len(cnic_groups) <= 1:
                # All same CNIC or no CNIC — keep as one cluster
                final_clusters.append(cluster)
            else:
                # Multiple different CNICs in one cluster = potential transitive error
                # Split by CNIC, assign no-CNIC records to the largest group
                sorted_groups = sorted(cnic_groups.values(), key=len, reverse=True)
                for i, group in enumerate(sorted_groups):
                    if i == 0:
                        group.extend(no_cnic)
                    final_clusters.append(set(group))

        # Cap cluster size to prevent mega-clusters
        MAX_CLUSTER_SIZE = 20
        capped_clusters = []
        for cluster in final_clusters:
            if len(cluster) > MAX_CLUSTER_SIZE:
                # Split into smaller chunks
                rids = sorted(list(cluster))
                for i in range(0, len(rids), MAX_CLUSTER_SIZE):
                    capped_clusters.append(set(rids[i:i + MAX_CLUSTER_SIZE]))
            else:
                capped_clusters.append(cluster)

        # Also add all singleton records (not in any cluster)
        clustered_rids = set()
        for c in capped_clusters:
            clustered_rids.update(c)
        for rid in record_map:
            if rid not in clustered_rids:
                capped_clusters.append({rid})

        # Sort clusters deterministically
        capped_clusters.sort(key=lambda c: sorted(list(c))[0])

        citizens = []
        for cluster_rids in capped_clusters:
            cluster_records = [record_map[rid] for rid in cluster_rids]
            citizens.append(self._merge_cluster(cluster_records))

        citizens_df = pd.DataFrame(citizens)

        # ── Save outputs (atomic writes to prevent corruption) ──
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

        def _atomic_csv_write(df, target_path):
            tmp_path = target_path.with_suffix(".csv.tmp")
            df.to_csv(tmp_path, index=False)
            os.replace(str(tmp_path), str(target_path))

        _atomic_csv_write(citizens_df, PROCESSED_DIR / "master_citizens.csv")

        if self.match_log:
            matches_df = pd.DataFrame(self.match_log)
            _atomic_csv_write(matches_df, PROCESSED_DIR / "entity_matches.csv")

        # ── Statistics ────────────────────────────────────────────
        merged_count = sum(1 for m in self.match_log if m["decision"] == "MERGED")
        review_count = sum(1 for m in self.match_log if m["decision"] == "REVIEW")
        conflict_count = sum(1 for m in self.match_log if m["decision"] == "CONFLICT")
        rejected_count = sum(1 for m in self.match_log if m["decision"] == "REJECTED")
        multi_record = sum(1 for c in capped_clusters if len(c) > 1)
        singleton = sum(1 for c in capped_clusters if len(c) == 1)

        print(f"\n  === Entity Resolution Results ===")
        print(f"  Input records: {len(all_records):,}")
        print(f"  Candidate pairs: {len(candidate_pairs):,}")
        print(f"  Merged pairs: {merged_count:,}")
        print(f"  Review pairs: {review_count:,}")
        print(f"  Conflict pairs: {conflict_count:,}")
        print(f"  Rejected pairs: {rejected_count:,}")
        print(f"  Final citizens: {len(citizens_df):,}")
        print(f"  Multi-record citizens: {multi_record:,}")
        print(f"  Singleton citizens: {singleton:,}")
        if multi_record > 0:
            sizes = [len(c) for c in capped_clusters if len(c) > 1]
            print(f"  Avg cluster size: {np.mean(sizes):.1f}")
            print(f"  Max cluster size: {max(sizes)}")

        return citizens_df

    def get_match_log(self) -> pd.DataFrame:
        """Return the match log as a DataFrame."""
        return pd.DataFrame(self.match_log) if self.match_log else pd.DataFrame()
