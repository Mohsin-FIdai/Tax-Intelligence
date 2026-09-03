import pandas as pd
from rapidfuzz import process as rapidfuzz_process, fuzz as rapidfuzz_fuzz
try:
    from thefuzz import process as thefuzz_process, fuzz as thefuzz_fuzz
except ImportError:
    thefuzz_process = rapidfuzz_process
    thefuzz_fuzz = rapidfuzz_fuzz
# Attempt to load urduhack for normalization, handling missing tensorflow gracefully
try:
    import sys
    # Patch sys.modules to bypass tensorflow import error in urduhack if TF is missing
    class DummyTF:
        class keras:
            class models:
                load_model = lambda *args, **kwargs: None
    sys.modules['tensorflow'] = DummyTF()
    from urduhack.normalization import normalize
except ImportError:
    def normalize(text):
        return text

try:
    from transliterate import translit
except ImportError:
    translit = lambda text, lang: text

from core.entity_resolution.roman_urdu import transliterate as custom_transliterate

def unify_query(query: str) -> tuple[str, str, str]:
    """
    Returns (clean_query, urdu_transliteration, transliterate_lib_output)
    """
    if not query:
        return "", "", ""
        
    query = str(query).strip()
    
    # 1. urduhack normalization (if it's already urdu)
    normalized = normalize(query)
    
    # 2. Custom Roman-to-Urdu (highly tuned for PK names)
    custom_urdu = custom_transliterate(normalized)
    
    # 3. Transliterate library fallback (e.g. Russian/etc. though not great for PK without packs)
    try:
        # Just use it as requested by the user, although it might fail for unsupported lang 'ur'
        lib_urdu = translit(normalized, 'ur')
    except Exception:
        lib_urdu = normalized
        
    return normalized, custom_urdu, lib_urdu


def soundex_words(name: str) -> list[str]:
    if not name:
        return []
    name = str(name).upper()
    soundex_mapping = {
        'B': '1', 'F': '1', 'P': '1', 'V': '1',
        'C': '2', 'G': '2', 'J': '2', 'K': '2', 'Q': '2', 'S': '2', 'X': '2', 'Z': '2',
        'D': '3', 'T': '3', 'L': '4', 'M': '5', 'N': '5', 'R': '6'
    }
    words = name.split()
    codes = []
    for word in words:
        word = ''.join(c for c in word if c.isalpha())
        if not word: continue
        first = word[0]
        code = first
        prev = soundex_mapping.get(first, '')
        for char in word[1:]:
            curr = soundex_mapping.get(char, '')
            if curr and curr != prev:
                code += curr
            if char not in 'HW':
                prev = curr
        codes.append((code + "000")[:4])
    return codes


def advanced_fuzzy_search(
    df: pd.DataFrame, 
    query: str, 
    search_columns: list[str] = ["canonical_name", "cnic"],
    limit: int = 50,
    score_cutoff: float = 75.0
) -> pd.DataFrame:
    """
    A unified search engine utilizing token intersection, soundex, urduhack, and transliteration.
    """
    if not query or df.empty:
        return pd.DataFrame(columns=df.columns)
        
    query_norm, query_urdu, query_translit = unify_query(query)
    clean_cnic = query.replace("-", "").strip()

    search_cols = list(search_columns)
    for extra_col in ["urdu_name", "father_name", "city", "province", "address"]:
        if extra_col in df.columns and extra_col not in search_cols:
            search_cols.append(extra_col)

    # Stage 1: Multi-token intersection across combined text
    words = [w for w in query_norm.lower().split() if len(w) > 1]
    if len(words) > 1:
        comb = pd.Series("", index=df.index)
        for col in search_cols:
            if col in df.columns:
                comb = comb + " " + df[col].astype(str).str.lower()
        
        all_words_mask = pd.Series(True, index=df.index)
        for w in words:
            all_words_mask = all_words_mask & comb.str.contains(w, regex=False)
            
        token_matches = df[all_words_mask]
        if len(token_matches) >= limit:
            return token_matches.head(limit)
    else:
        token_matches = pd.DataFrame(columns=df.columns)

    # Stage 2: Fast Exact / Substring Matching on individual columns
    masks = []
    for col in search_cols:
        if col not in df.columns: continue
        str_col = df[col].astype(str)
        if col == "cnic" and clean_cnic:
            masks.append(str_col.str.replace("-", "").str.contains(clean_cnic, case=False, na=False, regex=False))
        else:
            masks.append(str_col.str.contains(query_norm, case=False, na=False, regex=False))
            if query_urdu and query_urdu != query_norm:
                masks.append(str_col.str.contains(query_urdu, case=False, na=False, regex=False))
            if query_translit and query_translit != query_norm:
                masks.append(str_col.str.contains(query_translit, case=False, na=False, regex=False))
            
    if masks:
        final_mask = masks[0]
        for m in masks[1:]:
            final_mask = final_mask | m
        exact_matches = df[final_mask]
    else:
        exact_matches = pd.DataFrame(columns=df.columns)

    combined = pd.concat([token_matches, exact_matches]).drop_duplicates()
    if len(combined) >= limit:
        return combined.head(limit)

    # Stage 3: Soundex Phonetic Matching
    if "canonical_name" in df.columns:
        query_codes = set(soundex_words(query_norm))
        if query_codes:
            def has_soundex_match(name):
                return bool(query_codes.intersection(soundex_words(name)))
            
            soundex_mask = df["canonical_name"].apply(has_soundex_match)
            soundex_matches = df[soundex_mask]
            combined = pd.concat([combined, soundex_matches]).drop_duplicates()
            
    return combined.head(limit)
