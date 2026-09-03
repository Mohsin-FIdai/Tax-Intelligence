# -*- coding: utf-8 -*-
"""
Roman Urdu to Urdu Script Transliteration Map.
Provides basic dictionary-based lookups and character mappings for search purposes.
"""

# Common Pakistani name mappings
NAME_MAP = {
    "ali": "علی",
    "khan": "خان",
    "ahmed": "احمد",
    "raza": "رضا",
    "fatima": "فاطمہ",
    "hussain": "حسین",
    "muhammad": "محمد",
    "tariq": "طارق",
    "usman": "عثمان",
    "umar": "عمر",
    "abubakar": "ابوبکر",
    "khalid": "خالد",
    "bilal": "بلال",
    "raja": "راجا",
    "shah": "شاہ",
    "syed": "سید",
    "sheikh": "شیخ",
    "malik": "ملک",
    "iqbal": "اقبال",
    "kamran": "کامران",
    "imran": "عمران",
    "nawaz": "نواز",
    "zardari": "زرداری",
    "bhutto": "بھٹو",
    "javed": "جاوید",
    "nadeem": "ندیم",
    "tahir": "طاہر",
    "akbar": "اکبر",
    "qasim": "قاسم",
    "hamza": "حمزہ",
    "saad": "سعد",
    "zain": "زین",
    "ayesha": "(عائشہ|عایشہ)",
    "maryam": "(مریم|مریئم)",
    "zainab": "(زینب|زینب)",
    "sana": "(ثنا|ثناء|سنا|سناء)",
    "sara": "(سارہ|سارا)",
    "noor": "(نور|نور)",
    "amna": "آمنہ",
    "rabia": "رابعہ",
    "iqra": "اقرا",
    "hassan": "حسن",
    "abbas": "عباس",
    "mahmood": "محمود",
    "farooq": "فاروق",
    "qazi": "قاضی",
    "mirza": "مرزا",
    "hashmi": "ہاشمی",
    "virk": "ورک",
    "gondal": "گوندل",
    "mengal": "مینگل",
    "durrani": "درانی",
    "soomro": "سومرو",
    "cheema": "چیمہ",
    "sethi": "سیٹھی",
}

# Fallback character map for unknown words
CHAR_MAP = {
    "a": "ا", "b": "ب", "c": "س", "d": "د", "e": "ی",
    "f": "ف", "g": "گ", "h": "ہ", "i": "ی", "j": "ج",
    "k": "ک", "l": "ل", "m": "م", "n": "ن", "o": "و",
    "p": "پ", "q": "ق", "r": "ر", "s": "س", "t": "ت",
    "u": "ع", "v": "و", "w": "و", "x": "کس", "y": "ی", "z": "ز",
    "sh": "ش", "ch": "چ", "kh": "خ", "gh": "غ", "th": "تھ", "ph": "پھ"
}

def transliterate_word(word: str) -> str:
    """Transliterate a single Roman English word to Urdu script."""
    word = word.lower()
    if word in NAME_MAP:
        return NAME_MAP[word]
        
    urdu_word = ""
    i = 0
    while i < len(word):
        if i < len(word) - 1 and word[i:i+2] in CHAR_MAP:
            urdu_word += CHAR_MAP[word[i:i+2]]
            i += 2
        elif word[i] in CHAR_MAP:
            urdu_word += CHAR_MAP[word[i]]
            i += 1
        else:
            urdu_word += word[i]
            i += 1
    return urdu_word

def transliterate(text: str) -> str:
    """Transliterate Roman English text to Urdu (returns regex patterns if applicable)."""
    if not text:
        return ""
    words = text.split()
    return " ".join(transliterate_word(w) for w in words)

def transliterate_plain(text: str) -> str:
    """Transliterate Roman English text to a single clean Urdu string, stripping regex options."""
    import re
    res = transliterate(text)
    # Convert "(A|B|C)" to "A"
    res = re.sub(r"\(([^|]+)[^)]*\)", r"\1", res)
    return res
