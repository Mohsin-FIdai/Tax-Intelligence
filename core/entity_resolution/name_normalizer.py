"""
Name Normalisation Engine - Pakistani multilingual name cleaning with phonetic matching.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Dict, Any

from rapidfuzz import fuzz
try:
    import urduhack
    from urduhack.normalization import normalize as urdu_normalize
except ImportError:
    urdu_normalize = lambda x: x

# Urdu to English Mapping
_URDU_TO_ENG = {
    "ا": "a", "آ": "aa", "ب": "b", "پ": "p", "ت": "t", "ٹ": "t", "ث": "s",
    "ج": "j", "چ": "ch", "ح": "h", "خ": "kh", "د": "d", "ڈ": "d", "ذ": "z",
    "ر": "r", "ڑ": "r", "ز": "z", "ژ": "zh", "س": "s", "ش": "sh", "ص": "s",
    "ض": "z", "ط": "t", "ظ": "z", "ع": "a", "غ": "gh", "ف": "f", "ق": "q",
    "ک": "k", "گ": "g", "ل": "l", "م": "m", "ن": "n", "و": "w", "ہ": "h",
    "ی": "y", "ے": "e", "ئ": "i", "ں": "n", "ھ": "h"
}

def detect_script(text: str) -> str:
    """Detect if string is Urdu, English, or Mixed."""
    if not text: return "UNKNOWN"
    urdu_chars = sum(1 for c in text if "\u0600" <= c <= "\u06FF")
    total_chars = len(text.replace(" ", ""))
    if total_chars == 0: return "UNKNOWN"
    ratio = urdu_chars / total_chars
    if ratio > 0.8:
        return "URDU"
    elif ratio > 0.1:
        return "MIXED"
    elif re.search(r'[A-Za-z]', text):
        return "ENGLISH"  # Or Roman Urdu
    return "UNKNOWN"

def transliterate_urdu(text: str) -> str:
    """Basic character-level transliteration for Urdu to English"""
    res = ""
    for char in text:
        res += _URDU_TO_ENG.get(char, char)
    return res

# --- Canonical name mapping -----------------------
_NAME_VARIANTS: dict[str, list[str]] = {
    "Muhammad": ["Mohammad", "Mohammed", "Muhammed", "Muhamad", "Mohd", "Mohmd", "Muhmd",
                 "Mohamad", "Mohamed", "Md", "Muhd", "Mhd", "Mohmmad", "mhmd"],
    "Ahmad": ["Ahmed", "Ahmd", "Ahamed", "Ahamad"],
    "Ali": ["Alee", "Alli", "Aly"],
    "Hussain": ["Husain", "Husein", "Husayn", "Hossain", "Hossein", "Hussan", "Hussian"],
    "Hassan": ["Hasan", "Hasen", "Hasn"],
    "Usman": ["Osman", "Othman", "Uthman", "Usmaan", "asman"],
    "Imran": ["Emran", "Imraan"],
    "Bilal": ["Belal", "Bilaal"],
    "Ibrahim": ["Ibraheem", "Ebrahim", "Abrahim"],
    "Yusuf": ["Yousuf", "Yousaf", "Yoosuf", "Yousif", "Yousef", "Yusaf", "Josef"],
    "Omar": ["Umer", "Umar", "Umr"],
    "Hamza": ["Hamzah", "Hamzaa"],
    "Ismail": ["Ismael", "Esmail", "Ismaeel"],
    "Tariq": ["Tarik", "Tareq", "Tariq"],
    "Naveed": ["Navid", "Naweed"],
    "Waqas": ["Waqass", "Waqqas"],
    "Junaid": ["Juneid", "Juned"],
    "Rizwan": ["Rizwaan", "Rizvaan"],
    "Farhan": ["Farhaan"],
    "Adnan": ["Adnaan"],
    "Kashif": ["Kaashif"],
    "Nasir": ["Naseer", "Nasr"],
    "Salman": ["Salmaan", "Sulman"],
    "Arslan": ["Arsalan", "Arslaan"],
    "Faisal": ["Faysal", "Feisal"],
    "Khalid": ["Khaalid", "Khaleed"],
    "Iqbal": ["Eqbal", "Ikbal"],
    "Aisha": ["Ayesha", "Aisha", "Aysha", "Aesha"],
    "Fatima": ["Fathima", "Faatima", "Fatimah"],
    "Maryam": ["Mariam", "Meryem", "Miriam"],
    "Khadija": ["Khadeeja", "Khadijah"],
    "Zainab": ["Zaynab", "Zaineb", "Zenab"],
    "Noor": ["Nour", "Nur", "Noor"],
    "Sana": ["Sanaa", "Sanna"],
    "Khan": ["Khn", "Khaan"],
    "Chaudhry": ["Chaudhary", "Choudhry", "Choudhary", "Choudry", "Ch"],
    "Sheikh": ["Shaikh", "Shiekh", "Sh"],
    "Siddiqui": ["Siddique", "Siddiqi", "Siddiki", "Sidiqui"],
    "Qureshi": ["Quraishi", "Qurashi", "Kureshi"],
    "Butt": ["But", "Bhat", "Bhatt"],
    "Malik": ["Malick", "Malic"],
    "Awan": ["Awaan"],
    "Rajput": ["Rajpoot"],
    "Mughal": ["Moghal", "Moghul"],
    "Hashmi": ["Hashimi", "Hashmi"],
    "Abbasi": ["Abasi", "Abassi"],
    "Mehmood": ["Mahmood", "Mahmud", "Mehmud", "Mahmoud"],
    "Rashid": ["Rasheed", "Rashied"],
    "Syed": ["Sayyid", "Saied", "Sayyed", "Syeed"],
    "Rana": ["Raana"],
}

# Build reverse lookup: variant -> canonical
_VARIANT_TO_CANONICAL: dict[str, str] = {}
for canonical, variants in _NAME_VARIANTS.items():
    canonical_lower = canonical.lower()
    _VARIANT_TO_CANONICAL[canonical_lower] = canonical
    for v in variants:
        _VARIANT_TO_CANONICAL[v.lower()] = canonical

# --- Titles and honorifics to remove --------------------------------
_TITLES_RE = re.compile(
    r"\b(mr\.?|mrs\.?|ms\.?|dr\.?|prof\.?|haji|hajia|mian|ch\.?|sir|smt|begum|bibi|"
    r"engr\.?|advocate|adv\.?|justice|senator|general|gen\.?|col\.?|major|capt\.?|"
    r"brigadier|brig\.?|lt\.?|cmdr\.?)\b",
    re.IGNORECASE,
)
_EXTRA_SPACES = re.compile(r"\s{2,}")

# --- Soundex-like phonetic code for Pakistani names -----------------
_PHONETIC_MAP = {
    "b": "1", "f": "1", "p": "1", "v": "1",
    "c": "2", "g": "2", "j": "2", "k": "2", "q": "2", "s": "2", "x": "2", "z": "2",
    "d": "3", "t": "3",
    "l": "4",
    "m": "5", "n": "5",
    "r": "6",
}

def remove_titles(name: str) -> str:
    """Strip titles and honorifics from a name string."""
    cleaned = _TITLES_RE.sub("", name)
    cleaned = _EXTRA_SPACES.sub(" ", cleaned).strip()
    return cleaned

def _canonicalize_token(token: str) -> str:
    """Map a single name token to its canonical form."""
    return _VARIANT_TO_CANONICAL.get(token.lower(), token.title())

class NameRepresentation:
    def __init__(self, original: str):
        self.original = original
        self.script_type = detect_script(original)
        self.normalized_script = ""
        self.transliterated = ""
        self.canonical = ""
        self.tokens = []
        self.phonetic = ""
        self._process()
        
    def _process(self):
        if not self.original or self.original.lower().strip() in ("nan", "none", "", "null", "unknown", "n/a", "not available"):
            return
            
        name = self.original.strip()
        
        # 1. Normalize based on script
        if self.script_type in ("URDU", "MIXED"):
            name = urdu_normalize(name)
            self.normalized_script = name
            name_lat = transliterate_urdu(name)
        else:
            self.normalized_script = name
            name_lat = name
            
        # 2. English/Roman Urdu normalization
        name_lat = remove_titles(name_lat)
        name_lat = re.sub(r"[^\w\s-]", "", name_lat)
        self.transliterated = name_lat.lower().strip()
        
        # 3. Tokens & Canonicalization
        tokens = self.transliterated.split()
        self.tokens = [t for t in tokens if t]
        canonical_tokens = [_canonicalize_token(t) for t in self.tokens]
        self.canonical = " ".join(canonical_tokens)
        
        # 4. Phonetic code
        self.phonetic = phonetic_code(self.canonical)
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "original": self.original,
            "script_type": self.script_type,
            "normalized_script": self.normalized_script,
            "transliterated": self.transliterated,
            "canonical": self.canonical,
            "phonetic": self.phonetic
        }

@lru_cache(maxsize=None)
def parse_name(name: str) -> NameRepresentation:
    """Cache and return structured name representation."""
    return NameRepresentation(name)

def normalize_name(name: str | None) -> str:
    """Legacy backward compatibility method for entity matching."""
    if not name: return ""
    return parse_name(name).canonical

def phonetic_code(canonical_name: str) -> str:
    """Generate a Soundex-like phonetic code from canonical string."""
    if not canonical_name: return ""
    tokens = canonical_name.split()
    codes = []
    for token in tokens:
        if not token: continue
        code = token[0].upper()
        prev = ""
        for ch in token[1:]:
            mapped = _PHONETIC_MAP.get(ch, "0")
            if mapped != "0" and mapped != prev:
                code += mapped
                prev = mapped
            if len(code) >= 4:
                break
        code = code.ljust(4, "0")[:4]
        codes.append(code)
    return "-".join(codes[:3])

def get_phonetic(name: str | None) -> str:
    if not name: return ""
    return parse_name(name).phonetic

def name_similarity_score(name1: str, name2: str) -> dict:
    """
    Return a detailed similarity dictionary for cross-script and standard matches.
    Used by the confidence scorer.
    """
    rep1 = parse_name(name1)
    rep2 = parse_name(name2)
    
    if not rep1.canonical or not rep2.canonical:
        return {"score": 0.0, "reason": "Missing Name"}
        
    if rep1.canonical == rep2.canonical:
        if rep1.script_type != rep2.script_type:
            return {"score": 100.0, "reason": f"cross-script equivalent ({rep1.script_type} to {rep2.script_type})"}
        return {"score": 100.0, "reason": "exact match"}

    # Fuzzy match on canonical strings
    n1 = rep1.canonical
    n2 = rep2.canonical
    
    token_sort = fuzz.token_sort_ratio(n1, n2)
    token_set = fuzz.token_set_ratio(n1, n2)
    partial = fuzz.partial_ratio(n1, n2)
    
    phonetic_bonus = 10.0 if rep1.phonetic == rep2.phonetic and rep1.phonetic else 0.0
    
    score = (token_sort * 0.4 + token_set * 0.35 + partial * 0.25) + phonetic_bonus
    score = min(score, 100.0)
    
    reason = f"{int(score)}% similarity"
    if rep1.script_type != rep2.script_type:
        reason = f"cross-script {reason}"
        
    return {"score": score, "reason": reason}

def are_names_similar(name1: str, name2: str, threshold: float = 85.0) -> bool:
    """Legacy backward compatibility wrapper."""
    return name_similarity_score(name1, name2)["score"] >= threshold
