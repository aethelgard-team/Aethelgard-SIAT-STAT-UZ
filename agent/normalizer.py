"""
=============================================================================
Aethelgard SIAT: Deterministic Multi-Script, Multi-Language & Typo Normalizer
Fayl: agent/normalizer.py
Tavsif:
  O'zbekcha lotin (eski va yangi 'ç, ş, ğ, ō' alifbosi), O'zbekcha kirill,
  Rus tili, imlo xatolari, apostrofsiz shakllar, inversiyalar ('go'sht molniki')
  va ko'p savolli (compound) birikmalarni 0 ms kechikish bilan normallashtirish.
=============================================================================
"""

import re
from typing import Dict, List, Tuple, Any, Optional

# -----------------------------------------------------------------------------
# 1. Til va Alifbo Aniqlash (Language & Script Detection)
# -----------------------------------------------------------------------------

UZ_CYRL_CHARS = set("ўқғҳЎҚҒҲ")
UZ_CYRL_WORDS = {
    "қанча", "неча", "нечта", "нархи", "нархлари", "аҳоли", "сони",
    "гўшти", "гўшт", "бўлган", "бўлди", "йил", "йилда", "ойида",
    "вилояти", "шаҳри", "маош", "иш", "ҳақи", "истеъмол", "бозорлардаги",
    "тухум", "картошка", "шакар", "ун", "гуруч", "салом", "ассалому",
    "алайкум", "ёғи", "сути", "нони", "ўзбекистон", "тошкент", "самарқанд"
}

RU_WORDS = {
    "сколько", "стоит", "цена", "цены", "стоимость", "население", "численность",
    "говядина", "говядины", "баранина", "баранины", "яйца", "яиц", "картофель",
    "картошка", "зарплата", "заработная", "плата", "инфляция", "ввп",
    "ташкент", "ташкенте", "ташкентская", "узбекистан", "узбекистане", "самарканд",
    "фергана", "андижан", "бухара", "мясо", "мяса", "курица", "курятина",
    "мука", "муки", "сахар", "рис", "молоко", "хлеб", "масло", "бензин",
    "средняя", "динамика", "данные", "статистика", "привет", "здравствуйте",
    "помощь", "какой", "какая", "была", "году", "годах", "сентябре", "месяце",
    "биткоин", "биткоина", "доллар", "доллара", "погода", "погоду"
}

def detect_language_and_script(text: str) -> str:
    """
    Kiritilgan matn tilini aniqlaydi:
    - 'uz_cyrl': O'zbekcha kirill
    - 'ru': Rus tili
    - 'uz_latn': O'zbekcha lotin (standart yoki yangi alifbo)
    """
    if not text:
        return "uz_latn"
    
    t_lower = text.lower()

    # Agar o'zbek kirilliga xos harflar bo'lsa -> uz_cyrl
    if any(c in UZ_CYRL_CHARS for c in text):
        return "uz_cyrl"

    # Kirill harflari mavjudligini tekshirish
    has_cyrillic = bool(re.search(r"[\u0400-\u04FF]", text))
    if has_cyrillic:
        words = set(re.findall(r"[\u0400-\u04FF]+", t_lower))
        uz_matches = len(words & UZ_CYRL_WORDS)
        ru_matches = len(words & RU_WORDS)
        if uz_matches > ru_matches:
            return "uz_cyrl"
        if ru_matches > 0:
            return "ru"
        # Kirillcha so'roqlarda default qoida: agar ruscha belgilar ko'p bo'lsa ru, aks holda uz_cyrl
        return "ru"

    return "uz_latn"


# -----------------------------------------------------------------------------
# 2. Yangi O'zbek Lotin / Turkcha Belgilarni Transliteratsiya Qilish
# -----------------------------------------------------------------------------

NEW_LATIN_MAP = [
    ("ç", "ch"), ("Ç", "Ch"),
    ("ş", "sh"), ("Ş", "Sh"),
    ("ğ", "g'"), ("Ğ", "G'"),
    ("ō", "o'"), ("Ō", "O'"),
    ("ŏ", "o'"), ("Ŏ", "O'"),
    ("ö", "o'"), ("Ö", "O'"),
    ("ó", "o'"), ("Ó", "O'"),
    ("ñ", "ng"), ("Ñ", "Ng"),
    ("ı", "i"),  ("İ", "I"),
]

def transliterate_new_latin(text: str) -> str:
    """Yangi o'zbek lotin alifbosi (ç, ş, ğ, ō, ö, ó va h.k.) ni standart o'zbek lotiniga o'tkazish."""
    res = text
    for src, dst in NEW_LATIN_MAP:
        res = res.replace(src, dst)
    return res


# -----------------------------------------------------------------------------
# 3. O'zbekcha Kirill -> Lotin Transliteratsiyasi
# -----------------------------------------------------------------------------

CYRL_TO_LATN_MAP = {
    "ў": "o'", "Ў": "O'",
    "ғ": "g'", "Ғ": "G'",
    "қ": "q",   "Қ": "Q",
    "ҳ": "h",   "Ҳ": "H",
    "ш": "sh",  "Ш": "Sh",
    "ч": "ch",  "Ч": "Ch",
    "ё": "yo",  "Ё": "Yo",
    "ю": "yu",  "Ю": "Yu",
    "я": "ya",  "Я": "Ya",
    "ж": "j",   "Ж": "J",
    "й": "y",   "Й": "Y",
    "х": "x",   "Х": "X",
    "ц": "s",   "Ц": "S",
    "щ": "sh",  "Щ": "Sh",
    "ъ": "'",   "Ъ": "'",
    "ь": "'",   "Ь": "'",
    "а": "a",   "А": "A",
    "б": "b",   "Б": "B",
    "в": "v",   "В": "V",
    "г": "g",   "Г": "G",
    "д": "d",   "Д": "D",
    "е": "e",   "Е": "E",
    "з": "z",   "З": "Z",
    "и": "i",   "И": "I",
    "к": "k",   "К": "K",
    "л": "l",   "Л": "L",
    "м": "m",   "М": "M",
    "н": "n",   "Н": "N",
    "о": "o",   "О": "O",
    "п": "p",   "П": "P",
    "р": "r",   "Р": "R",
    "с": "s",   "С": "S",
    "т": "t",   "Т": "T",
    "у": "u",   "У": "U",
    "ф": "f",   "Ф": "F",
    "э": "e",   "Э": "E",
    "ы": "i",   "Ы": "I"
}

def cyrillic_to_latin_uz(text: str) -> str:
    """O'zbekcha kirill matnini standart o'zbekcha lotin alifbosiga to'g'ri o'tkazish."""
    if not text:
        return ""
    # So'z boshidagi 'Е / е' ni 'Ye / ye' qilish (masalan, 'Ер' -> 'Yer')
    res = re.sub(r"(?:\b|^)е", "ye", text)
    res = re.sub(r"(?:\b|^)Е", "Ye", res)
    for c, l in CYRL_TO_LATN_MAP.items():
        res = res.replace(c, l)
    return res


# -----------------------------------------------------------------------------
# 4. Ruscha -> O'zbekcha DWH Qidiruv Lug'ati (Deterministic 100+ Core Terms)
# -----------------------------------------------------------------------------

RU_TO_UZ_TERMS = [
    # Kelasi zamon va prognoz so'rovlari (Russian Future-Tense & Forecast)
    (r"\bсколько\s+будет\s+стоить\b", "narxi qancha bo'ladi"),
    (r"\bсколько\s+будут\s+стоить\b", "narxi qancha bo'ladi"),
    (r"\bбудет\s+стоить\b", "narxi bo'ladi"),
    (r"\bбудут\s+стоить\b", "narxi bo'ladi"),
    (r"\bстоить\b", "narxi"),
    (r"\bстоят\b", "narxi"),
    (r"\bсколько\s+станет\b", "qancha bo'ladi"),
    (r"\bсколько\s+составит\b", "qancha bo'ladi"),
    (r"\bстанет\b", "bo'ladi"),
    (r"\bсоставит\b", "bo'ladi"),
    (r"\bкакая\s+будет\s+цена\b", "narxi qancha bo'ladi"),
    (r"\bкакая\s+цена\s+будет\b", "narxi qancha bo'ladi"),
    (r"\bкакова\s+будет\s+цена\b", "narxi qancha bo'ladi"),
    (r"\bкакая\s+будет\b", "qanday bo'ladi"),
    (r"\bкакое\s+будет\b", "qanday bo'ladi"),
    (r"\bкакой\s+будет\b", "qanday bo'ladi"),
    (r"\bкакие\s+будут\b", "qanday bo'ladi"),
    (r"\bбудет\b", "bo'ladi"),
    (r"\bбудут\b", "bo'ladi"),
    (r"\bпрогноз\s+цен(?:ы)?(?:\s+на)?\b", "narxi prognozi"),
    (r"\bпрогноз\s+стоимости(?:\s+на)?\b", "narxi prognozi"),
    (r"\bпрогноз(?:ы|а|ов)?\b", "prognozi"),
    (r"\bпрогнозируется\b", "prognoz qilinadi"),
    (r"\bожидается\b", "kutilmoqda"),

    # Savol olmoshlari va harakatlar
    (r"\bсколько\s+стоил[аои]?\b", "narxi qancha edi"),
    (r"\bсколько\s+стоит\b", "narxi qancha"),
    (r"\bкакова\s+была\s+цена\b", "narxi qancha edi"),
    (r"\bкакая\s+была\s+цена\b", "narxi qancha edi"),
    (r"\bкакова\s+цена\b", "narxi qancha"),
    (r"\bкакая\s+цена\b", "narxi qancha"),
    (r"\bкаков[аоы]?\b", "qanday"),
    (r"\bкак(?:ая|ой|ое|ие)\b", "qanday"),
    (r"\bцена\b", "narxi"),
    (r"\bцены\b", "narxlari"),
    (r"\bстоимость\b", "narxi"),
    (r"\bдинамика\s+цен\b", "narxlar dinamikasi"),
    (r"\bсредн(?:яя|ей|юю)\s+цена\b", "o'rtacha narxi"),
    (r"\bсредн(?:ие|их)\s+цены\b", "o'rtacha narxlari"),
    (r"\b(?:какая\s+)?средн(?:яя|ей|юю)\s+(?:номинальная\s+)?(?:заработная\s+плата|зарплат[аыуеой])\b", "o'rtacha hisoblangan oylik ish haqi"),
    (r"\bсреднемесячная\s+(?:номинальная\s+)?заработная\s+плата\b", "o'rtacha hisoblangan oylik ish haqi"),
    (r"\b(?:заработная\s+плата|зарплат[аыуеой])\b", "o'rtacha hisoblangan oylik ish haqi"),
    (r"\bсредн(?:яя|ий|ее|ей|юю|их)\b", "o'rtacha"),
    (r"\bпочем\b", "narxi qancha"),

    # Oziq-ovqat va tovarlar
    (r"\bговядин[аыуеом]\b", "mol go'shti"),
    (r"\bбаранин[аыуеом]\b", "qo'y go'shti"),
    (r"\bмясо\s+птицы\b", "tovuq go'shti"),
    (r"\bкурятин[аыуеом]\b", "tovuq go'shti"),
    (r"\bкуриц[аыуеом]\b", "tovuq go'shti"),
    (r"\bмяс[оаеом]\b", "go'sht"),
    (r"\b(?:яйц[аоеу]|яйцах|яиц)\b", "tuxum"),
    (r"\bдесяток\s+яиц\b", "10 dona tuxum"),
    (r"\bкартофел[ьяеюем]\b", "kartoshka"),
    (r"\bкартошк[аиуеой]\b", "kartoshka"),
    (r"\bмук[аиуеой]\b", "un"),
    (r"\bсахар[аеом]?\b", "shakar"),
    (r"\bрис[аеом]?\b", "guruch"),
    (r"\bмолок[оаеом]\b", "sut"),
    (r"\bхлеб[аеом]?\b", "non"),
    (r"\bмасл[оаеом]\b", "yog'"),
    (r"\bподсолнечное\s+масло\b", "kungaboqar yog'i"),
    (r"\bбензин[аеом]?\b", "benzin"),

    # Iqtisodiy va demografik ko'rsatkichlar
    (r"\bчисленность\s+населения\b", "doimiy aholi soni"),
    (r"\bнаселени[еяюем]\b", "doimiy aholi soni"),
    (r"\bжителей\b", "doimiy aholi soni"),
    (r"\bсреднемесячная\s+номинальная\s+заработная\s+плата\b", "o'rtacha hisoblangan oylik ish haqi"),
    (r"\bуров(?:ень|ня)\s+средней\s+заработной\s+платы\b", "o'rtacha hisoblangan oylik ish haqi"),
    (r"\bуров(?:ень|ня)\s+средней\s+зарплаты\b", "o'rtacha hisoblangan oylik ish haqi"),
    (r"\bуров(?:ень|ня)\s+зарплаты\b", "o'rtacha hisoblangan oylik ish haqi"),
    (r"\bзаработная\s+плата\b", "o'rtacha hisoblangan oylik ish haqi"),
    (r"\bзарплат[аыуеой]\b", "o'rtacha hisoblangan oylik ish haqi"),
    (r"\bоклад[аеом]?\b", "ish haqi"),
    (r"\bввп\b", "yalpi ichki mahsulot"),
    (r"\bваловой\s+внутренний\s+продукт\b", "yalpi ichki mahsulot"),
    (r"\bврп\b", "yalpi hududiy mahsulot"),
    (r"\bуров(?:ень|ня)\s+инфляции\b", "iste'mol narxlari indeksi"),
    (r"\bинфляци[яиеюей]\b", "iste'mol narxlari indeksi"),
    (r"\bэкспорт[аеом]?\b", "tovarlar eksporti"),
    (r"\bимпорт[аеом]?\b", "tovarlar importi"),
    (r"\bбезработиц[аыуеой]\b", "ishsizlik darajasi"),
    (r"\bуровень\s+безработицы\b", "ishsizlik darajasi"),
    (r"\bуров[ень|ня|ню|нем|не]+\b", "darajasi"),

    # Vaqt va davrlar (Ruscha)
    (r"\bв\s+январе\b", "yanvarda"),
    (r"\bв\s+феврале\b", "fevralda"),
    (r"\bв\s+марте\b", "martda"),
    (r"\bв\s+апреле\b", "aprelda"),
    (r"\bв\s+мае\b", "mayda"),
    (r"\bв\s+июне\b", "iyunda"),
    (r"\bв\s+июле\b", "iyulda"),
    (r"\bв\s+августе\b", "avgustda"),
    (r"\bв\s+сентябре\b", "sentyabrda"),
    (r"\bв\s+октябре\b", "oktyabrda"),
    (r"\bв\s+ноябре\b", "noyabrda"),
    (r"\bв\s+декабре\b", "dekabrda"),
    (r"\bянвар[ьяе]\b", "yanvar"),
    (r"\bфеврал[ьяе]\b", "fevral"),
    (r"\bмарт[ае]?\b", "mart"),
    (r"\bапрел[ьяе]\b", "aprel"),
    (r"\bмай\b", "may"),
    (r"\bиюн[ьяе]\b", "iyun"),
    (r"\bиюл[ьяе]\b", "iyul"),
    (r"\bавгуст[ае]?\b", "avgust"),
    (r"\bсентябр[ьяе]\b", "sentyabr"),
    (r"\bоктябр[ьяе]\b", "oktyabr"),
    (r"\bноябр[ьяе]\b", "noyabr"),
    (r"\bдекабр[ьяе]\b", "dekabr"),
    (r"\bквартал[ае]?\b", "chorak"),
    (r"\b(?:в|на)\s*(\d{4})\s*(?:-?й)?\s*год[ауеом]?\b", r"\1-yilda"),
    (r"\b(\d{4})\s*год[ауеом]?\b", r"\1-yilda"),
    (r"\b(?:в|на)\s*(\d{4})\b", r"\1-yilda"),
    (r"\bгод[ауеом]?\b", "yil"),
    (r"\bсейчас\b", "hozir"),
    (r"\bпоследние\s+данные\b", "oxirgi ma'lumotlar"),

    # 14 ta Hudud (Ruscha nomlar)
    (r"\bташкентск(?:ая|ой|ую)\s+област[ьие]\b", "Toshkent viloyati"),
    (r"\bв\s+ташкентской\s+области\b", "Toshkent viloyati"),
    (r"\bг\.?\s*ташкент[ае]?\b", "Toshkent shahri"),
    (r"\bгород\s+ташкент[ае]?\b", "Toshkent shahri"),
    (r"\bв\s+ташкенте\b", "Toshkent shahri"),
    (r"\bташкент[ае]?\b", "Toshkent shahri"),
    (r"\bсамаркандск(?:ая|ой|ую)\s+област[ьие]\b", "Samarqand viloyati"),
    (r"\bв\s+самарканде\b", "Samarqand viloyati"),
    (r"\bсамарканд[ае]?\b", "Samarqand viloyati"),
    (r"\bферганск(?:ая|ой|ую)\s+област[ьие]\b", "Farg'ona viloyati"),
    (r"\bв\s+фергане\b", "Farg'ona viloyati"),
    (r"\bферган[аые]\b", "Farg'ona viloyati"),
    (r"\bандижанск(?:ая|ой|ую)\s+област[ьие]\b", "Andijon viloyati"),
    (r"\bв\s+андижане\b", "Andijon viloyati"),
    (r"\bандижан[ае]?\b", "Andijon viloyati"),
    (r"\bбухарск(?:ая|ой|ую)\s+област[ьие]\b", "Buxoro viloyati"),
    (r"\bв\s+бухаре\b", "Buxoro viloyati"),
    (r"\bбухар[аые]\b", "Buxoro viloyati"),
    (r"\bнаманганск(?:ая|ой|ую)\s+област[ьие]\b", "Namangan viloyati"),
    (r"\bв\s+намангане\b", "Namangan viloyati"),
    (r"\bнаманган[ае]?\b", "Namangan viloyati"),
    (r"\bкашкадарьинск(?:ая|ой|ую)\s+област[ьие]\b", "Qashqadaryo viloyati"),
    (r"\bв\s+кашкадарье\b", "Qashqadaryo viloyati"),
    (r"\bкашкадарь[яе]\b", "Qashqadaryo viloyati"),
    (r"\bсурхандарьинск(?:ая|ой|ую)\s+област[ьие]\b", "Surxondaryo viloyati"),
    (r"\bв\s+сурхандарье\b", "Surxondaryo viloyati"),
    (r"\bсурхандарь[яе]\b", "Surxondaryo viloyati"),
    (r"\bнавоийск(?:ая|ой|ую)\s+област[ьие]\b", "Navoiy viloyati"),
    (r"\bв\s+навои\b", "Navoiy viloyati"),
    (r"\bнавои\b", "Navoiy viloyati"),
    (r"\bджизакск(?:ая|ой|ую)\s+област[ьие]\b", "Jizzax viloyati"),
    (r"\bв\s+джизаке\b", "Jizzax viloyati"),
    (r"\bджизак[ае]?\b", "Jizzax viloyati"),
    (r"\bсырдарьинск(?:ая|ой|ую)\s+област[ьие]\b", "Sirdaryo viloyati"),
    (r"\bв\s+сырдарье\b", "Sirdaryo viloyati"),
    (r"\bсырдарь[яе]\b", "Sirdaryo viloyati"),
    (r"\bхорезмск(?:ая|ой|ую)\s+област[ьие]\b", "Xorazm viloyati"),
    (r"\bв\s+хорезме\b", "Xorazm viloyati"),
    (r"\bхорезм[ае]?\b", "Xorazm viloyati"),
    (r"\bкаракалпакстан\b", "Qoraqalpog'iston Respublikasi"),
    (r"\bреспублика\s+каракалпакстан\b", "Qoraqalpog'iston Respublikasi"),
    (r"\bкаракалпакия\b", "Qoraqalpog'iston Respublikasi"),
    (r"\bнукус[ае]?\b", "Qoraqalpog'iston Respublikasi"),
    (r"\bузбекистан[ае]?\b", "O'zbekiston Respublikasi"),
    (r"\bв\s+узбекистане\b", "O'zbekiston Respublikasi"),
]

def translate_russian_to_uzbek(text: str) -> str:
    """Rus tilidagi so'rovlarni o'zbekcha standart statistik terminlarga normallashtirish."""
    res = text
    for pattern, replacement in RU_TO_UZ_TERMS:
        res = re.sub(pattern, replacement, res, flags=re.IGNORECASE)
    return res


# -----------------------------------------------------------------------------
# 5. Apostroflar va Imlo Xatolarini Normallashtirish (Typo & Morphology)
# -----------------------------------------------------------------------------

TYPO_RULES = [
    # Missing apostrophes in common words
    (r"\bgoshti\b", "go'shti"),
    (r"\bgosht\b", "go'sht"),
    (r"\bqoyi\b", "qo'yi"),
    (r"\bqoy\b", "qo'y"),
    (r"\btovuk\b", "tovuq"),
    (r"\byogi\b", "yog'i"),
    (r"\byog\b", "yog'"),

    # Inverted / possessive forms (go'sht molniki -> mol go'shti)
    (r"\bgo['`]?sht\s+molniki\b", "mol go'shti"),
    (r"\bmolniki\b", "mol go'shti"),
    (r"\bgo['`]?sht\s+qo['`]?yniki\b", "qo'y go'shti"),
    (r"\bqo['`]?yniki\b", "qo'y go'shti"),
    (r"\bgo['`]?sht\s+tovuqniki\b", "tovuq go'shti"),
    (r"\btovuqniki\b", "tovuq go'shti"),

    # h <-> x xatolari
    (r"\bnarh([ia-z]*)\b", r"narx\1"),
    (r"\btuhum([a-z]*)\b", r"tuxum\1"),
    (r"\bgo['`]?sh\b", "go'sht"),

    # Tovar nomlari imlo xatolari
    (r"\bkartowk([a-z]*)\b", r"kartoshk\1"),
    (r"\bkartoshk\b", "kartoshka"),
    (r"\bkartoshka([a-z]*)\b", "kartoshka"),

    # So'zlashuv / qisqartmalar (rekursiv takrorlanishdan himoyalangan)
    (r"\bnechpul\b", "narxi qancha"),
    (r"\bnecha\s+pul\b", "narxi qancha"),
    (r"\bnechi\s+pul\b", "narxi qancha"),
    (r"\bdoimiy\s+aholi(?:si)?(?:\s+soni)?\b", "doimiy aholi soni"),
    (r"\b(?<!doimiy\s)aholi(?:si)?\s+soni\b", "doimiy aholi soni"),
    (r"\bodam\s+soni\b", "doimiy aholi soni"),
    (r"\bnechta\s+odam\b", "doimiy aholi soni"),
    (r"\bodam\s+yashaydi\b", "doimiy aholi soni"),
    (r"\bkishi\s+yashaydi\b", "doimiy aholi soni"),
    (r"\b(?<!doimiy\s)(?:nechta|qancha)\s+aholi(?:si)?(?!\s+zichlig)\b", "doimiy aholi soni"),
    (r"\b(?<!doimiy\s)aholi(?:si)?(?!\s+zichlig)(?:\s+(?:nechta|qancha))?\b", "doimiy aholi soni"),
    (r"\bo['`]?rtacha\s+hisoblangan\s+oylik\s+ish\s+haqi\b", "o'rtacha hisoblangan oylik ish haqi"),
    (r"\bo['`]?rtacha\s+(?:hisoblangan\s+)?(?:oylik\s+)?maosh\b", "o'rtacha hisoblangan oylik ish haqi"),
    (r"\bo['`]?rtacha\s+hisoblangan\s+oylik(?!\s+ish\s+haqi)\b", "o'rtacha hisoblangan oylik ish haqi"),
    (r"\bo['`]?rtacha\s+oylik(?!\s+ish\s+haqi)\b", "o'rtacha hisoblangan oylik ish haqi"),
    (r"\boylik\s+maosh\b", "o'rtacha hisoblangan oylik ish haqi"),
    (r"\bmaoshlar\b", "o'rtacha hisoblangan oylik ish haqi"),
    (r"\bmaosh\b", "o'rtacha hisoblangan oylik ish haqi"),
    (r"\b(?<!hisoblangan\s)oyliklar\b", "o'rtacha hisoblangan oylik ish haqi"),
    (r"\b(?<!hisoblangan\s)oylik(?!\s+ish\s+haqi)\b", "o'rtacha hisoblangan oylik ish haqi"),

    # Oylarning imlo variantlari
    (r"\bsentabr\b", "sentyabr"),
    (r"\boktabr\b", "oktyabr"),

    # Sana formatlari: 09.2026 -> 2026-M09
    (r"\b0?(\d)\.20(\d{2})\b", r"20\2-M0\1"),
    (r"\b1([0-2])\.20(\d{2})\b", r"20\2-M1\1"),
    (r"\b0?(\d)/20(\d{2})\b", r"20\2-M0\1"),
    (r"\b1([0-2])/20(\d{2})\b", r"20\2-M1\1"),
]

def strip_apostrophes(text: str) -> str:
    """Apostroflardan butunlay tozalangan shakl (dual search uchun)."""
    return re.sub(r"['`’‘ʻ´]", "", text)

def standardize_apostrophes(text: str) -> str:
    """Barcha apostrof variantlarini yagona (') belgiga keltirish."""
    return re.sub(r"[`’‘ʻ´]", "'", text)

def normalize_typos_and_morphology(text: str) -> str:
    """So'zlashuv, inversiya va imlo xatolarini normallashtirish."""
    res = text
    for pat, rep in TYPO_RULES:
        res = re.sub(pat, rep, res, flags=re.IGNORECASE)
    # Takrorlanishlarni tozalash
    res = re.sub(r"\b(o['`]?rtacha\s+)+", "o'rtacha ", res, flags=re.IGNORECASE)
    res = re.sub(r"\b(hisoblangan\s+)+", "hisoblangan ", res, flags=re.IGNORECASE)
    res = re.sub(r"\b(oylik\s+)+", "oylik ", res, flags=re.IGNORECASE)
    res = re.sub(r"\b(ish\s+haqi\s*)+", "ish haqi ", res, flags=re.IGNORECASE)
    return res.strip()


# -----------------------------------------------------------------------------
# 6.6. Prognoz va Kelajak So'rovlarini Aniqlash (Forecast Intent Detection)
# -----------------------------------------------------------------------------

FORECAST_KEYWORDS_PATTERNS = [
    # Uzbek Latin
    r"\bprognoz(?:i|lar|lari|lash|ga)?\b",
    r"\bbashorat(?:i|lar|lari|lash|ga)?\b",
    r"\bkelajak(?:da|gi|dagi)?\b",
    r"\bkutilmoqda\b",
    r"\bkutiladi\b",
    r"\bkutilayotgan\b",
    r"\bbo['`]?ladi\b",
    r"\bboladi\b",
    r"\bbo['`]?lishi\b",
    r"\byetadi\b",
    # Uzbek Cyrillic
    r"\bпрогноз(?:и|лар|лари|лаш|га)?\b",
    r"\bбашорат(?:и|лар|лари|лаш|га)?\b",
    r"\bкелажак(?:да|ги|даги)?\b",
    r"\bкутилмоқда\b",
    r"\bкутилади\b",
    r"\bбўлади\b",
    r"\bетади\b",
    # Russian
    r"\bпрогноз(?:ы|а|ов|ирование)?\b",
    r"\bспрогнозируй(?:те)?\b",
    r"\bбудет\b",
    r"\bбудут\b",
    r"\bожидает(?:ся|мые|мый)\b",
    r"\bперспектив[аые]\b",
]

OUT_OF_SCOPE_PATTERNS = [
    r"\b(?:bitcoin|bitkoin|kripto|криптовалют)\b",
    r"\b(?:ob-havo|obhavo|weather|погода)\b",
    r"\b(?:kurs\s+dollar|valyuta\s+kursi|dollar\s+kursi|курс\s+доллара)\b",
    r"\b(?:futbol|sport|kino|film|qo'shiq|музыка)\b"
]

def is_out_of_scope_query(text: str) -> bool:
    """SIAT doirasiga kirmaydigan mavzular (kripto, ob-havo, valyuta kursi va h.k.) ni aniqlaydi."""
    t = text.lower()
    return any(bool(re.search(pat, t)) for pat in OUT_OF_SCOPE_PATTERNS)

def detect_forecast_intent(text: str, years: Optional[List[int]] = None) -> Dict[str, Any]:
    """
    So'rovda kelajak prognozi niyati (2027-2036) yoki prognoz kalit so'zlari
    mavjudligini aniqlaydi.
    """
    t_lower = text.lower()
    extracted_years = years if years is not None else [int(y) for y in re.findall(r"\b(1[89]\d\d|20\d\d)\b", t_lower)]
    
    has_keyword = any(bool(re.search(pat, t_lower)) for pat in FORECAST_KEYWORDS_PATTERNS)
    future_years = [y for y in extracted_years if y >= 2027]
    
    is_forecast = False
    target_year: Optional[int] = None
    is_extreme = False
    
    if future_years:
        max_y = max(future_years)
        is_forecast = True
        target_year = max_y
        if max_y > 2036:
            is_extreme = True
    elif has_keyword:
        is_forecast = True
        # Yil aytilmagan bo'lsa, bazadagi oxirgi yildan keyingi yil (2027) ga mo'ljallanadi
        target_year = 2027
        
    return {
        "is_forecast": is_forecast,
        "target_year": target_year,
        "is_extreme_forecast": is_extreme,
        "has_forecast_keyword": has_keyword
    }

GREETING_PATTERNS = [
    r"^\s*(?:assalomu\s+alaykum|assalom\s+alaykum|salom|hayrli\s+kun|qalaysiz|qandaysiz)\s*[.!?]?\s*$",
    r"^\s*(?:ассалому\s+алайкум|салом|хайрли\s+кун|қалайсиз|қандайсиз)\s*[.!?]?\s*$",
    r"^\s*(?:привет|здравствуйте|добрый\s+день|добрый\s+вечер|хай)\s*[.!?]?\s*$",
    r"^\s*(?:yordam|help|помощь|ko'mak|qanday\s+ishlatiladi)\s*[.!?]?\s*$"
]

GREETING_RESPONSES = {
    "uz_latn": (
        "Assalomu alaykum! Men **Aethelgard · SIAT** — O'zbekiston Davlat statistika agentligining "
        "(SIAT / stat.uz) 3 232 ta rasmiy ko'rsatkichi va 2.58 milliondan ortiq tasdiqlangan faktlari "
        "asosida ishlovchi sun'iy intellekt tahlilchisiman [1].\n\n"
        "Sizga quyidagi statistik ma'lumotlarni taqdim eta olaman:\n"
        "• *\"2026-yil sentyabrda mol go'shti narxi qancha edi?\"*\n"
        "• *\"O'zbekistonda doimiy aholi soni qancha?\"*\n"
        "• *\"Toshkent shahri va viloyatlarda o'rtacha oylik maosh qancha?\"*\n\n"
        "Qaysi ko'rsatkich bo'yicha ma'lumot kerak?"
    ),
    "uz_cyrl": (
        "Ассалому алайкум! Мен **Aethelgard · SIAT** — Ўзбекистон Давлат статистика агентлигининг "
        "(SIAT / stat.uz) 3 232 та расмий кўрсаткичи ва 2.58 миллиондан ортиқ тасдиқланган фактлари "
        "асосида ишловчи сунъий интеллект таҳлилчисиман [1].\n\n"
        "Сизга қуйидаги статистик маълумотларни тақдим эта оламан:\n"
        "• *«2026 йил сентябрда мол гўшти нархи қанча эди?»*\n"
        "• *«Ўзбекистонда доимий аҳоли сони қанча?»*\n"
        "• *«Тошкент шаҳри ва вилоятларда ўртача ойлик иш ҳақи қанча?»*\n\n"
        "Қайси кўрсаткич бўйича маълумот керак?"
    ),
    "ru": (
        "Здравствуйте! Я **Aethelgard · SIAT** — интеллектуальный аналитик открытых данных Агентства статистики "
        "при Президенте Республики Узбекистан (SIAT / stat.uz), охватывающий 3 232 официальных показателя "
        "и более 2.58 млн подтвержденных фактов с гарантией нулевой галлюцинации [1].\n\n"
        "Вы можете запросить любую официальную статистику, например:\n"
        "• *«Сколько стоила говядина в сентябре 2026 года?»*\n"
        "• *«Какова численность постоянного населения Узбекистана?»*\n"
        "• *«Какая средняя зарплата в Ташкенте?»*\n\n"
        "Какой статистический показатель вас интересует?"
    )
}

def is_greeting_query(text: str) -> bool:
    """So'rov sof salomlashish yoki yordam so'rash ekanligini tekshiradi."""
    t = text.strip()
    return any(re.match(pat, t, re.IGNORECASE) for pat in GREETING_PATTERNS)

def get_greeting_response(lang: str) -> str:
    """Mos til va alifboda samimiy salomlashuv javobini qaytaradi."""
    return GREETING_RESPONSES.get(lang, GREETING_RESPONSES["uz_latn"])


# -----------------------------------------------------------------------------
# 6.5. Inson Tushunadigan Davr Formatlagich (Human-Readable Period Formatting)
# -----------------------------------------------------------------------------

def format_period_label(period_code: str, lang: str = "uz_latn") -> str:
    """
    DWH davr kodini (2026-M09, 2025-Y00, 2026-Q03, 2025) inson tushunadigan
    chiroyli formatga o'tkazadi.
    """
    if not period_code:
        return ""
    code = str(period_code).strip()

    # 1. Oylik: YYYY-M01 .. YYYY-M12
    m_match = re.match(r"^(\d{4})-M0?([1-9]|1[0-2])$", code, re.IGNORECASE)
    if m_match:
        year, month_num = m_match.group(1), int(m_match.group(2))
        month_names_uz = {
            1: "yanvar", 2: "fevral", 3: "mart", 4: "aprel",
            5: "may", 6: "iyun", 7: "iyul", 8: "avgust",
            9: "sentyabr", 10: "oktyabr", 11: "noyabr", 12: "dekabr"
        }
        month_names_cyrl = {
            1: "январь", 2: "февраль", 3: "март", 4: "апрель",
            5: "май", 6: "июнь", 7: "июль", 8: "август",
            9: "сентябрь", 10: "октябрь", 11: "ноябрь", 12: "декабрь"
        }
        month_names_ru = {
            1: "январь", 2: "февраль", 3: "март", 4: "апрель",
            5: "май", 6: "июнь", 7: "июль", 8: "август",
            9: "сентябрь", 10: "октябрь", 11: "ноябрь", 12: "декабрь"
        }
        if lang == "ru":
            return f"{month_names_ru.get(month_num, '')} {year} года"
        elif lang == "uz_cyrl":
            return f"{year} йил {month_names_cyrl.get(month_num, '')} ойи"
        else:
            return f"{year}-yil {month_names_uz.get(month_num, '')} oyi"

    # 2. Choraklik: YYYY-Q01 .. YYYY-Q04 yoki YYYY-Q1 .. YYYY-Q4
    q_match = re.match(r"^(\d{4})-Q0?([1-4])$", code, re.IGNORECASE)
    if q_match:
        year, q_num = q_match.group(1), int(q_match.group(2))
        if lang == "ru":
            return f"{q_num}-й квартал {year} года"
        elif lang == "uz_cyrl":
            return f"{year} йил {q_num}-чорак"
        else:
            return f"{year}-yil {q_num}-chorak"

    # 3. Yillik: YYYY-Y00 yoki 4 ta raqamli YYYY
    y_match = re.match(r"^(\d{4})(?:-Y00)?$", code, re.IGNORECASE)
    if y_match:
        year = y_match.group(1)
        if lang == "ru":
            return f"{year} год"
        elif lang == "uz_cyrl":
            return f"{year} йил"
        else:
            return f"{year}-yil"

    return code


def format_compact_period(period_code: str, lang: str = "uz_latn") -> str:
    """Grafiklar o'qi va hover uchun ixcham davr nomi (masalan, '2026 sen')."""
    if not period_code:
        return ""
    code = str(period_code).strip()
    m_match = re.match(r"^(\d{4})-M0?([1-9]|1[0-2])$", code, re.IGNORECASE)
    if m_match:
        year, month_num = m_match.group(1), int(m_match.group(2))
        months_short = {
            1: "yan", 2: "fev", 3: "mar", 4: "apr",
            5: "may", 6: "iyn", 7: "iyl", 8: "avg",
            9: "sen", 10: "okt", 11: "noy", 12: "dek"
        }
        return f"{year} {months_short.get(month_num, '')}"
    return format_period_label(code, lang)


# -----------------------------------------------------------------------------
# 7. Ko'p Savolli / Murakkab So'rovlarni Ajratish (Compound Splitting)
# -----------------------------------------------------------------------------

def split_compound_query(query: str) -> List[str]:
    """
    Agar foydalanuvchi bitta xabarda 2-3 ta mustaqil savol bergan bo'lsa
    (masalan: 'mol go'sht narxi, tuxum narxi ?' yoki 'Toshkent aholisi va o'rtacha maosh qancha?'),
    ularni mustaqil sub-so'rovlarga ajratadi.
    Oddiy sanalar yoki hududlar ('2026-yil, sentyabr', 'Toshkent, 2025') ajratilmaydi.
    """
    q = query.strip()
    if not q:
        return [query]

    # Split belgilari: '?', ',', ' va ', ' hamda ', ' и '
    # Dastlab '?' bo'yicha ajratish
    raw_parts = [p.strip() for p in re.split(r"[?]+", q) if p.strip()]
    if len(raw_parts) > 1 and len(raw_parts) <= 3:
        # Har bir bo'lak haqiqiy savol yoki yo'qligini tekshirish
        valid_sub = []
        for p in raw_parts:
            if len(p) >= 3 and any(c.isalpha() for c in p):
                valid_sub.append(p)
        if len(valid_sub) > 1:
            return valid_sub[:3]

    # Agar '?' bo'yicha bo'linmasa, vergul yoki ' va / hamda / и ' bo'yicha tekshirish
    split_regex = r"(?:,\s*|\s+\bva\b\s+|\s+\bhamda\b\s+|\s+\bи\b\s+)"
    parts = [p.strip() for p in re.split(split_regex, q, flags=re.IGNORECASE) if p.strip()]

    # Faqat har bir qismda mustaqil mazmun (tovar/ko'rsatkich yoki so'rov predmeti) bo'lsa
    # (masalan: 'mol go'sht narxi' va 'tuxum narxi')
    indicator_stems = (
        "go'sht", "gosht", "mol", "qo'y", "qoy", "tovuq", "tuxum", "narx", "narh",
        "aholi", "soni", "maosh", "oylik", "ish haqi", "haqi", "yaim", "inflyatsi",
        "un", "kartoshk", "shakar", "benzin", "eksport", "import", "ishsizlik",
        "говядин", "яйц", "зарплат", "населен", "ввп", "инфляц"
    )

    sub_queries = []
    for p in parts:
        clean_p = p.strip(" ?!,.")
        p_words = set(re.findall(r"[a-zA-Z\u0400-\u04FF']+", clean_p.lower()))
        # Agar oddiy sana/yil yoki faqat bitta hudud bo'lsa (masalan '2026-yil' yoki 'sentyabr'), ajratilmaydi
        is_substantive = any(stem in clean_p.lower() for stem in indicator_stems) or len(p_words) >= 3
        if is_substantive and len(clean_p) >= 4:
            sub_queries.append(clean_p)

    if len(sub_queries) >= 2 and len(sub_queries) <= 3:
        return sub_queries

    return [query]


# -----------------------------------------------------------------------------
# 8. Umumlashtirilgan Yagona Normallashtirish Funksiyasi (Main Pipeline)
# -----------------------------------------------------------------------------

def normalize_input_query(query: str) -> Dict[str, Any]:
    """
    Har qanday tildagi, alifbodagi va formatdagi so'rovni tahlil qilib,
    DWH uchun standart kanonik O'zbekcha lotin qidiruv so'zlariga va metama'lumotlarga keltiradi.
    """
    raw = query.strip()
    lang = detect_language_and_script(raw)

    is_greeting = is_greeting_query(raw)

    # 1. Alifbo va tilni kanonik lotinga o'tkazish
    step1 = raw
    if lang == "uz_latn":
        step1 = transliterate_new_latin(step1)
    elif lang == "uz_cyrl":
        step1 = cyrillic_to_latin_uz(step1)
    elif lang == "ru":
        # Ruscha so'zlarni o'zbekcha ekvivalentlariga o'tkazamiz
        step1 = translate_russian_to_uzbek(step1)
        # Qolgan kirill harflarini lotinga o'tkazamiz
        step1 = cyrillic_to_latin_uz(step1)

    # Apostroflarni standartlash
    step2 = standardize_apostrophes(step1)

    # Imlo xatolari, inversiya ('go'sht molniki') va morfologiya
    step3 = normalize_typos_and_morphology(step2)

    forecast_info = detect_forecast_intent(raw)
    out_of_scope = is_out_of_scope_query(raw)

    # Kelajak prognoz so'rovlarida RRF qidiruvini toza kanonik ko'rsatkichga yo'naltirish
    # uchun kelasi zamon va prognoz to'ldiruvchi so'zlari tozalanadi
    if forecast_info["is_forecast"]:
        # 1. Ruscha va transliteratsiya qilingan kelasi zamon to'ldiruvchilari
        clean_s = re.sub(
            r"\b(?:skol'?ko\s+budet\s+stoit'?|budet\s+stoit'?|skol'?ko\s+stanet|skol'?ko\s+sostavit|skol'?ko|budet|budut|stoit'?|stoyat|stanet|sostavit)\b",
            " ", step3, flags=re.IGNORECASE
        )
        clean_s = re.sub(
            r"\b(?:kak(?:aya|oy|oe|ie)\s+budet(?:\s+tsena)?|kak(?:aya|oy|oe|ie)\b)",
            " ", clean_s, flags=re.IGNORECASE
        )
        clean_s = re.sub(
            r"\b(?:skolko\s+budet\s+stoit|budet\s+stoit|skolko|stoit)\b",
            " ", clean_s, flags=re.IGNORECASE
        )
        # 2. O'zbekcha lotin kelasi zamon va prognoz to'ldiruvchilari
        clean_s = re.sub(
            r"\b(?:qanday\s+bo['`]?ladi|qanday|qancha\s+bo['`]?ladi|necha\s+bo['`]?ladi|qancha\s+boladi|necha\s+boladi|bo['`]?ladi|boladi|bo['`]?lishi|bolishi|qancha|necha|nechta)\b",
            " ", clean_s, flags=re.IGNORECASE
        )
        clean_s = re.sub(
            r"\b(?:prognoz(?:i|lar|lari|lash|ga)?|bashorat(?:i|lar|lari|lash|ga)?|kutilmoqda|kutiladi|kutilayotgan|yetadi)\b",
            " ", clean_s, flags=re.IGNORECASE
        )
        # 3. O'zbekcha kirill kelasi zamon va prognoz to'ldiruvchilari
        clean_s = re.sub(
            r"\b(?:қандай\s+бўлади|қандай|қанча\s+бўлади|неча\s+бўлади|бўлади|прогноз(?:и|лар|лари|лаш|га)?|башорат(?:и)?|кутилмоқда|кутилади|қанча|неча)\b",
            " ", clean_s, flags=re.IGNORECASE
        )
        # 4. Yil va davr shovqinlarini tozalash
        clean_s = re.sub(r"\b(1[89]\d\d|20\d\d)(?:-yil(?:da|ga)?)?\b", " ", clean_s)
        clean_s = re.sub(r"\b(1[89]\d\d|20\d\d)\s*йил(?:да|га)?\b", " ", clean_s)
        clean_s = re.sub(r"\byil(?:da|ga|i|dagi|gi)?\b", " ", clean_s)
        clean_s = re.sub(r"\bйил(?:да|га|и)?\b", " ", clean_s)
        clean_s = re.sub(r"\b(?:v|na)\s*(\d{4})\b", " ", clean_s, flags=re.IGNORECASE)
        clean_s = re.sub(r"\b(?:в|на)\s*(\d{4})\b", " ", clean_s, flags=re.IGNORECASE)
        clean_s = re.sub(r"\s+", " ", clean_s).strip(" ?!,.")

        # 5. Oziq-ovqat narxi so'rovlari: agar oziq-ovqat mahsuloti bo'lsa va narx so'ralgan bo'lsa,
        # 'narxi' so'zini qo'shib yoki inversiyani to'g'rilab, to'g'ridan-to'g'ri #1308 ko'rsatkichga yo'naltirish
        food_items = [
            "mol go'shti", "qo'y go'shti", "tovuq go'shti", "tuxum", "kartoshka",
            "un", "shakar", "guruch", "sut", "non", "yog'", "kungaboqar yog'i"
        ]
        has_food = any(fi in clean_s.lower() for fi in food_items)
        raw_has_price = bool(re.search(r"\b(?:стоить|стоит|стоят|стоил[аои]?|цена|цены|стоимость|narx|narxi|narxlari|qancha|почем|baho)\b", raw, re.IGNORECASE))
        if has_food and raw_has_price and "narx" not in clean_s.lower():
            clean_s = f"{clean_s} narxi"
        clean_s = re.sub(
            r"^\s*narxi\s+(mol go'shti|qo'y go'shti|tovuq go'shti|tuxum|kartoshka|un|shakar|guruch|non|sut|yog')\b",
            r"\1 narxi",
            clean_s,
            flags=re.IGNORECASE
        )

        if clean_s:
            canonical_uz = clean_s
        else:
            canonical_uz = step3.strip()
    else:
        canonical_uz = step3.strip()

    de_apostrophed = strip_apostrophes(canonical_uz)

    # Umumiy mahsulot so'rovi (masalan faqat "go'sht narxi" deganda mol, qo'y, tovuq ko'rsatish)
    is_generic_meat = bool(re.search(r"\bgo['`]?sht\s+(?:narxi|qancha|bo['`]?lyapti)\b", canonical_uz.lower())) and not any(
        sp in canonical_uz.lower() for sp in ("mol", "qo'y", "qoy", "tovuq", "molniki", "qo'yniki")
    )

    return {
        "raw_query": raw,
        "response_lang": lang,
        "canonical_uz": canonical_uz,
        "de_apostrophed": de_apostrophed,
        "is_greeting": is_greeting,
        "is_generic_meat": is_generic_meat,
        "is_out_of_scope": out_of_scope,
        "is_forecast": forecast_info["is_forecast"],
        "target_year": forecast_info["target_year"],
        "is_extreme_forecast": forecast_info["is_extreme_forecast"],
        "has_forecast_keyword": forecast_info["has_forecast_keyword"],
        "sub_queries": split_compound_query(raw)
    }


# Qulaylik va to'g'ridan-to'g'ri import uchun alias
normalize_query = normalize_input_query
