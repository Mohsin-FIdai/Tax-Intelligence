"""
Confidence Scorer - Computes match probability between two candidate records.

Scoring Strategy:
- Score is normalized to 0-100 based on AVAILABLE comparable fields only
- Missing fields don't penalize the score
- But identifier strength hierarchy is enforced:
  VERY STRONG: exact valid CNIC (alone is strong evidence)
  STRONG: CNIC + name, CNIC + father, CNIC + phone, phone + name + location
  MEDIUM: name + father + city
  WEAK: name only, city only (never merge on weak evidence alone)
"""
import re
from rapidfuzz import fuzz

from config.settings import (
    ER_CNIC_WEIGHT, ER_PHONE_WEIGHT, ER_NAME_WEIGHT, ER_CITY_WEIGHT, ER_ADDRESS_WEIGHT,
    ER_NTN_WEIGHT, ER_FATHER_NAME_WEIGHT,
    ER_NAME_EXACT_THRESHOLD, ER_NAME_PARTIAL_THRESHOLD, ER_NAME_CONFLICT_THRESHOLD,
)
from core.entity_resolution.name_normalizer import name_similarity_score


_ADDR_STRIP_RE = re.compile(r"\b(house|h|st|street|block|sector)\b", re.IGNORECASE)


def _exact_match(a: str, b: str) -> bool:
    if not a or not b:
        return False
    return a.strip().lower() == b.strip().lower()


def _fuzzy_score(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a.lower() == b.lower():
        return 100.0
    return float(fuzz.token_sort_ratio(a.lower(), b.lower()))


def score_match(record1: dict, record2: dict) -> float:
    """Compute an overall match confidence (0-100) between two records.
    
    Score is normalized by AVAILABLE comparable fields, not total possible weight.
    This prevents sparse records from being unfairly penalized.
    """
    earned_weight = 0.0
    available_weight = 0.0

    cnic1 = record1.get("_cnic_normalized", "")
    cnic2 = record2.get("_cnic_normalized", "")
    if cnic1 and cnic2:
        available_weight += ER_CNIC_WEIGHT
        if cnic1 == cnic2:
            earned_weight += ER_CNIC_WEIGHT

    ntn1 = record1.get("_ntn_normalized", "")
    ntn2 = record2.get("_ntn_normalized", "")
    if ntn1 and ntn2:
        available_weight += ER_NTN_WEIGHT
        if ntn1 == ntn2:
            earned_weight += ER_NTN_WEIGHT

    phone1 = record1.get("_phone_normalized", "")
    phone2 = record2.get("_phone_normalized", "")
    if phone1 and phone2:
        available_weight += ER_PHONE_WEIGHT
        if phone1 == phone2:
            earned_weight += ER_PHONE_WEIGHT

    city1 = record1.get("_city_normalized", "")
    city2 = record2.get("_city_normalized", "")
    if city1 and city2:
        available_weight += ER_CITY_WEIGHT
        if city1 == city2:
            cscore = 100.0
        else:
            cscore = _fuzzy_score(city1, city2)
        if cscore >= 80:
            earned_weight += ER_CITY_WEIGHT * (cscore / 100)

    name1 = record1.get("_name_normalized", "")
    name2 = record2.get("_name_normalized", "")
    if name1 and name2:
        available_weight += ER_NAME_WEIGHT
        if name1 == name2:
            earned_weight += ER_NAME_WEIGHT
        else:
            n_dict = name_similarity_score(name1, name2)
            nscore = n_dict["score"]
            if nscore >= ER_NAME_EXACT_THRESHOLD:
                earned_weight += ER_NAME_WEIGHT
            elif nscore >= ER_NAME_PARTIAL_THRESHOLD:
                earned_weight += ER_NAME_WEIGHT * (nscore / 100)

    addr1 = record1.get("_address_normalized", "")
    addr2 = record2.get("_address_normalized", "")
    if addr1 and addr2:
        available_weight += ER_ADDRESS_WEIGHT
        if addr1 == addr2:
            ascore = 100.0
        else:
            a1_norm = _ADDR_STRIP_RE.sub("", addr1).strip()
            a2_norm = _ADDR_STRIP_RE.sub("", addr2).strip()
            ascore = _fuzzy_score(a1_norm, a2_norm)
        if ascore >= 70:
            earned_weight += ER_ADDRESS_WEIGHT * (ascore / 100)

    fname1 = record1.get("_father_name_normalized", "")
    fname2 = record2.get("_father_name_normalized", "")
    if fname1 and fname2:
        available_weight += ER_FATHER_NAME_WEIGHT
        if fname1 == fname2:
            earned_weight += ER_FATHER_NAME_WEIGHT
        else:
            f_dict = name_similarity_score(fname1, fname2)
            fscore = f_dict["score"]
            if fscore >= ER_NAME_EXACT_THRESHOLD:
                earned_weight += ER_FATHER_NAME_WEIGHT
            elif fscore >= ER_NAME_PARTIAL_THRESHOLD:
                earned_weight += ER_FATHER_NAME_WEIGHT * (fscore / 100)

    if available_weight == 0:
        return 0.0

    confidence = (earned_weight / available_weight) * 100.0
    return round(confidence, 1)


def explain_match(record1: dict, record2: dict) -> dict:
    """Return matching reasons, risk level, merge reason, confidence, and decision."""
    def has_min_fields(rec: dict) -> bool:
        cnic = rec.get("_cnic_normalized", "")
        name = rec.get("_name_normalized", "")
        fname = rec.get("_father_name_normalized", "")
        phone = rec.get("_phone_normalized", "")
        addr = rec.get("_address_normalized", "")
        
        # Helper to check if value is actually populated and not a placeholder/missing
        def is_val(v):
            if not v:
                return False
            val_clean = str(v).strip().lower()
            return val_clean not in ["", "nan", "unknown", "none", "null", "undefined", "n/a", "unknown name", "unknown father name", "unknown cnic"]
            
        has_c = is_val(cnic)
        has_n = is_val(name)
        has_f = is_val(fname)
        has_p = is_val(phone)
        has_a = is_val(addr)
        
        # If CNIC is present, we must have at least 1 other populated field to prevent matching empty-profile records.
        if has_c:
            return sum(1 for x in [has_n, has_f, has_p, has_a] if x) >= 1
            
        # If no CNIC, require at least 3 other fields to be safe.
        return sum(1 for x in [has_n, has_f, has_p, has_a] if x) >= 3

    if not has_min_fields(record1) or not has_min_fields(record2):
        return {
            "decision": "REJECTED",
            "confidence": 0.0,
            "reasons": [],
            "risk_level": "Low Risk",
            "merge_reason": "Missing Primary Fields (Need CNIC or at least 2 other fields)"
        }

    reasons: list[dict] = []
    earned_weight = 0.0
    available_weight = 0.0

    def _add(field, v1, v2, match_type, raw_score):
        if raw_score > 0:
            reasons.append({
                "field": field,
                "value_left": v1,
                "value_right": v2,
                "match_type": match_type,
                "score": round(raw_score, 1),
            })

    def _mask_cnic(val: str) -> str:
        if not val:
            return ""
        val = val.replace("-", "")
        return f"***********{val[-4:]}" if len(val) >= 4 else "****"

    def _mask_phone(val: str) -> str:
        if not val:
            return ""
        val = val.replace("-", "")
        return f"*******{val[-4:]}" if len(val) >= 4 else "****"

    cnic_exact = False
    name_similar = False
    father_similar = False
    phone_exact = False
    address_similar = False
    cnic_conflict = False
    name_conflict = False
    city_match = False

    cnic1 = record1.get("_cnic_normalized", "")
    cnic2 = record2.get("_cnic_normalized", "")
    if cnic1 and cnic2:
        available_weight += ER_CNIC_WEIGHT
        if cnic1 == cnic2:
            _add("CNIC", _mask_cnic(cnic1), _mask_cnic(cnic2), "exact", ER_CNIC_WEIGHT)
            earned_weight += ER_CNIC_WEIGHT
            cnic_exact = True
        else:
            cnic_conflict = True

    ntn1 = record1.get("_ntn_normalized", "")
    ntn2 = record2.get("_ntn_normalized", "")
    if ntn1 and ntn2:
        available_weight += ER_NTN_WEIGHT
        if ntn1 == ntn2:
            _add("NTN", ntn1, ntn2, "exact", ER_NTN_WEIGHT)
            earned_weight += ER_NTN_WEIGHT

    phone1 = record1.get("_phone_normalized", "")
    phone2 = record2.get("_phone_normalized", "")
    if phone1 and phone2:
        available_weight += ER_PHONE_WEIGHT
        if phone1 == phone2:
            _add("Phone", _mask_phone(phone1), _mask_phone(phone2), "exact", ER_PHONE_WEIGHT)
            earned_weight += ER_PHONE_WEIGHT
            phone_exact = True

    city1 = record1.get("_city_normalized", "")
    city2 = record2.get("_city_normalized", "")
    if city1 and city2:
        available_weight += ER_CITY_WEIGHT
        if city1 == city2:
            cscore = 100.0
        else:
            cscore = _fuzzy_score(city1, city2)
        if cscore >= 80:
            c_earned = ER_CITY_WEIGHT * (cscore / 100)
            earned_weight += c_earned
            _add("City", city1, city2, "fuzzy", c_earned)
            city_match = True

    name1 = record1.get("_name_normalized", "")
    name2 = record2.get("_name_normalized", "")
    if name1 and name2:
        available_weight += ER_NAME_WEIGHT
        if name1 == name2:
            _add("Name", name1, name2, "exact", ER_NAME_WEIGHT)
            earned_weight += ER_NAME_WEIGHT
            name_similar = True
        else:
            ns_dict = name_similarity_score(name1, name2)
            ns = ns_dict["score"]
            match_reason = ns_dict.get("reason", "fuzzy")
            if ns >= ER_NAME_EXACT_THRESHOLD:
                _add(f"Name ({match_reason})", name1, name2, "near_exact", ER_NAME_WEIGHT)
                earned_weight += ER_NAME_WEIGHT
                name_similar = True
            elif ns >= ER_NAME_PARTIAL_THRESHOLD:
                n_earned = ER_NAME_WEIGHT * ns / 100
                _add(f"Name ({match_reason})", name1, name2, "fuzzy", n_earned)
                earned_weight += n_earned
                name_similar = True
            elif ns < ER_NAME_CONFLICT_THRESHOLD:
                name_conflict = True

    addr1 = record1.get("_address_normalized", "")
    addr2 = record2.get("_address_normalized", "")
    if addr1 and addr2:
        available_weight += ER_ADDRESS_WEIGHT
        if addr1 == addr2:
            ascore = 100.0
        else:
            a1_norm = _ADDR_STRIP_RE.sub("", addr1).strip()
            a2_norm = _ADDR_STRIP_RE.sub("", addr2).strip()
            ascore = _fuzzy_score(a1_norm, a2_norm)
        if ascore >= 70:
            a_earned = ER_ADDRESS_WEIGHT * ascore / 100
            _add("Address", addr1, addr2, "fuzzy", a_earned)
            earned_weight += a_earned
            address_similar = True

    fname1 = record1.get("_father_name_normalized", "")
    fname2 = record2.get("_father_name_normalized", "")
    if fname1 and fname2:
        available_weight += ER_FATHER_NAME_WEIGHT
        if fname1 == fname2:
            _add("Father Name", fname1, fname2, "exact", ER_FATHER_NAME_WEIGHT)
            earned_weight += ER_FATHER_NAME_WEIGHT
            father_similar = True
        else:
            f_dict = name_similarity_score(fname1, fname2)
            fscore = f_dict["score"]
            if fscore >= ER_NAME_EXACT_THRESHOLD:
                _add("Father Name", fname1, fname2, "near_exact", ER_FATHER_NAME_WEIGHT)
                earned_weight += ER_FATHER_NAME_WEIGHT
                father_similar = True
            elif fscore >= ER_NAME_PARTIAL_THRESHOLD:
                f_earned = ER_FATHER_NAME_WEIGHT * fscore / 100
                _add("Father Name", fname1, fname2, "fuzzy", f_earned)
                earned_weight += f_earned
                father_similar = True

    # 🌟🌟 Decision Engine 🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟
    decision = "REVIEW"
    risk_level = "Medium Risk"
    merge_reason = "Review Required"

    overall_confidence = round((earned_weight / available_weight) * 100.0, 1) if available_weight > 0 else 0.0

    # Penalize confidence if CNIC is completely different or not present when Name/Father match
    if name_similar and father_similar and not cnic_exact:
        other_evidence = phone_exact or city_match or address_similar
        if cnic_conflict:
            # Completely different CNIC -> major penalty
            overall_confidence *= 0.5
        else:
            # CNIC not present -> moderate penalty, mitigated by other evidence
            if other_evidence:
                overall_confidence *= 0.8
            else:
                overall_confidence *= 0.6
        overall_confidence = round(overall_confidence, 1)

    # 1. Hard conflicts: different CNIC but shared identifiers
    # Exclude cases where Name + Father Name strictly match, because we'll auto-merge them below
    if cnic_conflict and (name_similar or phone_exact) and not (name_similar and father_similar):
        risk_level = "High Risk"
        merge_reason = "Conflict: Shared Identifiers but Different CNIC"
        decision = "CONFLICT"
    elif phone_exact and name_conflict and not cnic_exact:
        risk_level = "High Risk"
        merge_reason = "Conflict: Shared Phone but Completely Different Names"
        decision = "CONFLICT"

    # 2. AUTO-MERGE tiers
    elif cnic_exact and name_similar and father_similar:
        risk_level = "Low Risk"
        merge_reason = "Auto Merge: Exact CNIC + Name + Father Name"
        decision = "MERGED"
        overall_confidence = 100.0
    elif cnic_exact and (name_similar or father_similar or phone_exact):
        risk_level = "Low Risk"
        merge_reason = "Auto Merge: Exact CNIC + Supporting Match"
        decision = "MERGED"
    elif name_similar and father_similar:
        other_matches = []
        if phone_exact: other_matches.append("Phone")
        if address_similar: other_matches.append("Address")
        if city_match: other_matches.append("City")
        
        if len(other_matches) >= 1:
            risk_level = "Medium Risk"
            others_str = " + ".join(other_matches)
            merge_reason = f"Auto Merge: Name + Father Name + {others_str} (No CNIC)"
            decision = "MERGED"
            overall_confidence = 75.0 if len(other_matches) == 1 else 80.0
        else:
            risk_level = "Medium Risk"
            merge_reason = "Auto Merge: Name + Father Name (No CNIC)"
            decision = "MERGED"
            overall_confidence = 70.0

    # 3. REVIEW: some evidence but not enough for auto-merge
    elif cnic_exact and not name_similar and not father_similar:
        risk_level = "Medium Risk"
        merge_reason = "Review: CNIC matches but Name/Father differs"
    elif phone_exact and name_similar:
        risk_level = "Medium Risk"
        merge_reason = "Review: Phone + Name match, needs more evidence"
    elif (not cnic1 or not cnic2) and sum([name_similar, father_similar, phone_exact, address_similar, city_match]) >= 2:
        risk_level = "Medium Risk"
        merge_reason = "Review: CNIC missing but 2+ fields match strongly"
        decision = "REVIEW"
    elif overall_confidence >= 50:
        risk_level = "Medium Risk"
        merge_reason = "Review: Moderate confidence, partial identifier match"

    # 4. REJECT: insufficient evidence
    else:
        decision = "REJECTED"
        risk_level = "Low Risk"
        merge_reason = "Insufficient Evidence"

    # 5. Promote: 100% confidence REVIEW → auto-merge
    if decision == "REVIEW" and overall_confidence >= 100.0:
        decision = "MERGED"
        risk_level = "Low Risk"
        merge_reason = "Auto Merge: Maximum confidence across matched fields"

    return {
        "decision": decision,
        "confidence": overall_confidence,
        "reasons": reasons,
        "risk_level": risk_level,
        "merge_reason": merge_reason
    }
