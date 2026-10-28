# Part of odoo_pdi. See LICENSE file for full copyright and licensing details.
"""Interpreta el texto que devuelve el OCR de una INE.

Módulo de Python puro (no depende de Odoo ni de Pillow): recibe texto y
devuelve datos estructurados y validados.

* **Frente:** nombre, domicilio, clave de elector, CURP, fecha de nacimiento,
  sexo, sección, emisión y vigencia.
* **Reverso:** zona de lectura mecánica (MRZ, formato TD1 de la OACI) con
  nombre, fecha de nacimiento, sexo y vencimiento, protegidos por dígitos
  verificadores.

El OCR comete errores típicos (0/O, 1/I, 5/S, 8/B), así que las cadenas con
estructura fija se corrigen según el tipo de carácter que se espera en cada
posición, y los datos se cruzan entre sí (la CURP trae la fecha de nacimiento y
el sexo; el MRZ repite nombre, nacimiento y sexo).
"""
import difflib
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date

# --------------------------------------------------------------------------
# Constantes
# --------------------------------------------------------------------------

# Diccionario oficial para el dígito verificador de la CURP.
CURP_DICTIONARY = "0123456789ABCDEFGHIJKLMNÑOPQRSTUVWXYZ"
# Claves de entidad federativa de la CURP (NE = nacido en el extranjero).
CURP_STATES = frozenset({
    "AS", "BC", "BS", "CC", "CL", "CM", "CS", "CH", "DF", "DG", "GT", "GR",
    "HG", "JC", "MC", "MN", "MS", "NT", "NL", "OC", "PL", "QT", "QR", "SP",
    "SL", "SR", "TC", "TS", "TL", "VZ", "YN", "ZS", "NE",
})

_TO_DIGIT = str.maketrans({
    "O": "0", "Q": "0", "D": "0", "I": "1", "L": "1", "|": "1",
    "Z": "2", "S": "5", "G": "6", "B": "8",
})
_TO_LETTER = str.maketrans({
    "0": "O", "1": "I", "2": "Z", "5": "S", "6": "G", "8": "B",
})

_NAME_CHARS = re.compile(r"[^A-ZÁÉÍÓÚÜÑ ]")
_DATE_RE = re.compile(r"(\d{2})\s*[/\-.\s]\s*(\d{2})\s*[/\-.\s]\s*(\d{4})")
_CURP_RE = re.compile(r"^[A-Z]{4}\d{6}[HMX][A-Z]{2}[B-DF-HJ-NP-TV-Z]{3}[A-Z0-9]\d$")
_ELECTOR_RE = re.compile(r"^[A-Z]{6}\d{8}[HM]\d{3}$")
_MRZ_LINE2_RE = re.compile(r"^[0-9OQDILSZGB|]{7}[HMFX<][0-9OQDILSZGB|]{7}")

# Etiquetas del frente de la credencial.
LABEL_NAME = "NOMBRE"
LABEL_ADDRESS = "DOMICILIO"
LABEL_ELECTOR = "CLAVE DE ELECTOR"
LABEL_CURP = "CURP"
LABEL_BIRTH = "FECHA DE NACIMIENTO"
LABEL_SEX = "SEXO"
_STOP_LABELS = (LABEL_ELECTOR, LABEL_CURP, LABEL_BIRTH, LABEL_SEX)


# --------------------------------------------------------------------------
# Resultado
# --------------------------------------------------------------------------

@dataclass
class IneData:
    """Datos extraídos de una INE.

    ``confidence`` guarda, por campo, un valor de 0 a 1: 1 = validado con un
    dígito verificador; 0.8 = leído tal cual; 0.5 o menos = corregido o
    deducido. ``warnings`` lista inconsistencias que el usuario debe revisar.
    """

    first_name: str = None
    paternal_surname: str = None
    maternal_surname: str = None
    curp: str = None
    elector_key: str = None
    birth_date: date = None
    sex: str = None  # "H" (hombre) o "M" (mujer)
    birth_state_code: str = None
    street: str = None
    street2: str = None
    zip: str = None
    city: str = None
    state: str = None
    section: str = None
    registration_year: int = None
    emission_year: int = None
    validity_year: int = None
    confidence: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)

    @property
    def gender(self):
        return {"H": "male", "M": "female"}.get(self.sex)

    @property
    def full_name(self):
        """Nombre completo en orden «nombres apellidos»."""
        parts = (self.first_name, self.paternal_surname, self.maternal_surname)
        return " ".join(part for part in parts if part)

    def to_dict(self):
        """Representación serializable a JSON."""
        data = {}
        for key, value in self.__dict__.items():
            data[key] = value.isoformat() if isinstance(value, date) else value
        return data


# --------------------------------------------------------------------------
# Utilidades de texto
# --------------------------------------------------------------------------

def _strip_accents(text):
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _norm(text):
    """Mayúsculas, sin acentos (Ñ incluida) y con espacios colapsados."""
    return " ".join(_strip_accents(text.upper()).split())


def _lines(text):
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


def _similar(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()


def _after_label(line, label, threshold=0.78):
    """Si ``line`` empieza con ``label`` (con tolerancia a errores del OCR),
    devuelve el resto de la línea; si no, ``None``.

    Se permite una palabra de basura al inicio (por ejemplo, ``| NOMBRE``).
    """
    words = line.split()
    count = len(label.split())
    for offset in (0, 1):
        head = _norm(" ".join(words[offset:offset + count]))
        if head and _similar(head, label) >= threshold:
            return " ".join(words[offset + count:])
    return None


def _find_label(lines, label, start=0):
    """Índice de la primera línea (desde ``start``) que lleva la etiqueta."""
    for index in range(start, len(lines)):
        if _after_label(lines[index], label) is not None:
            return index
    return None


def _clean_name(line):
    # En un nombre no hay dígitos: los que aparecen son letras mal leídas.
    text = _NAME_CHARS.sub(" ", line.upper().translate(_TO_LETTER))
    # Los caracteres sueltos son ruido del OCR, no parte de un nombre.
    return " ".join(token for token in text.split() if len(token) > 1)


def _valid_date(year, month, day):
    try:
        return date(year, month, day)
    except ValueError:
        return None


# --------------------------------------------------------------------------
# CURP y clave de elector
# --------------------------------------------------------------------------

def curp_check_digit(curp17):
    """Dígito verificador (0-9) de los primeros 17 caracteres de una CURP."""
    total = sum(
        CURP_DICTIONARY.index(char) * (18 - position)
        for position, char in enumerate(curp17)
    )
    return (10 - total % 10) % 10


def parse_curp(raw):
    """Valida y corrige una CURP leída por el OCR.

    :return: ``dict`` con ``curp``, ``birth_date``, ``sex``, ``state_code``,
        ``check_ok`` y ``fixes`` (caracteres corregidos), o ``None`` si no
        tiene la estructura de una CURP.
    """
    candidate = re.sub(r"[^A-Z0-9]", "", raw.upper())
    if len(candidate) != 18:
        return None
    chars, fixes = [], 0
    for position, char in enumerate(candidate):
        if position < 4 or position in (11, 12, 13, 14, 15):
            expected = "letter"
        elif position == 10:
            expected = "sex"
        elif position == 16:
            expected = "any"
        else:
            expected = "digit"
        fixed = char
        if expected == "letter" and char.isdigit():
            fixed = char.translate(_TO_LETTER)
        elif expected == "digit" and not char.isdigit():
            fixed = char.translate(_TO_DIGIT)
        elif expected == "sex" and char not in "HMX":
            fixed = {"N": "H", "W": "M"}.get(char, char)
        if fixed != char:
            fixes += 1
        chars.append(fixed)
    curp = "".join(chars)
    if not _CURP_RE.match(curp):
        return None
    # La homoclave es un dígito para nacidos hasta 1999 y una letra desde 2000.
    century = 2000 if curp[16].isalpha() else 1900
    birth = _valid_date(
        century + int(curp[4:6]), int(curp[6:8]), int(curp[8:10])
    )
    if not birth:
        return None
    return {
        "curp": curp,
        "birth_date": birth,
        "sex": "H" if curp[10] == "H" else "M" if curp[10] == "M" else None,
        "state_code": curp[11:13],
        "check_ok": curp_check_digit(curp[:17]) == int(curp[17]),
        "fixes": fixes,
    }


def parse_elector_key(raw):
    """Valida y corrige una clave de elector (6 letras, 6 dígitos de fecha,
    2 de entidad, sexo y 3 dígitos). Devuelve la clave o ``None``."""
    candidate = re.sub(r"[^A-Z0-9]", "", raw.upper())
    if len(candidate) != 18:
        return None
    chars = []
    for position, char in enumerate(candidate):
        if position < 6:
            char = char.translate(_TO_LETTER) if char.isdigit() else char
        elif position == 14:
            char = {"N": "H", "W": "M"}.get(char, char)
        elif not char.isdigit():
            char = char.translate(_TO_DIGIT)
        chars.append(char)
    key = "".join(chars)
    if not _ELECTOR_RE.match(key):
        return None
    month, day = int(key[8:10]), int(key[10:12])
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return None
    return key


def _windows(text, size):
    return (text[i:i + size] for i in range(len(text) - size + 1))


def _find_curp(lines):
    best, best_score = None, None
    for line in lines:
        rest = _after_label(line, LABEL_CURP)
        labeled = rest is not None
        compact = re.sub(r"[^A-Z0-9]", "", (rest if labeled else _norm(line)))
        for window in _windows(compact, 18):
            parsed = parse_curp(window)
            if not parsed:
                continue
            score = (4 if parsed["check_ok"] else 0) + (2 if labeled else 0) - parsed["fixes"]
            if best_score is None or score > best_score:
                best, best_score = parsed, score
    return best


def _find_elector_key(lines):
    best, best_score = None, None
    for line in lines:
        rest = _after_label(line, LABEL_ELECTOR)
        labeled = rest is not None
        compact = re.sub(r"[^A-Z0-9]", "", (rest if labeled else _norm(line)))
        for window in _windows(compact, 18):
            key = parse_elector_key(window)
            if not key:
                continue
            score = (2 if labeled else 0) - sum(a != b for a, b in zip(key, window))
            if best_score is None or score > best_score:
                best, best_score = key, score
    return best


# --------------------------------------------------------------------------
# Frente de la INE
# --------------------------------------------------------------------------

def _parse_names(lines, data):
    start = _find_label(lines, LABEL_NAME)
    if start is None:
        return
    end = _find_label(lines, LABEL_ADDRESS, start + 1)
    block = lines[start + 1:end if end is not None else start + 5]
    names = [name for name in (_clean_name(line) for line in block) if name]
    if len(names) >= 3:
        data.paternal_surname, data.maternal_surname = names[0], names[1]
        data.first_name = " ".join(names[2:])
        score = 0.8
    elif len(names) == 2:
        data.paternal_surname, data.first_name = names
        data.warnings.append(
            "Solo se detectaron dos líneas de nombre: se tomó la primera como "
            "apellido paterno y la segunda como nombre. Revisa los apellidos."
        )
        score = 0.5
    elif len(names) == 1:
        data.first_name = names[0]
        data.warnings.append("Solo se detectó una línea de nombre. Revisa el nombre completo.")
        score = 0.3
    else:
        return
    for key in ("first_name", "paternal_surname", "maternal_surname"):
        if getattr(data, key):
            data.confidence[key] = score


def _parse_address(lines, data):
    start = _find_label(lines, LABEL_ADDRESS)
    if start is None:
        return
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if any(_after_label(lines[index], label) is not None for label in _STOP_LABELS):
            end = index
            break
    block = [re.sub(r"[^A-Z0-9ÁÉÍÓÚÜÑ .,#/°\-]", " ", line.upper()) for line in lines[start + 1:end]]
    block = [" ".join(line.split()) for line in block if line.strip()]
    if not block:
        return
    zip_match = re.search(r"\b(\d{5})\b", " ".join(block))
    if zip_match:
        data.zip = zip_match.group(1)
        block = [" ".join(line.replace(data.zip, " ").split()) for line in block]
        block = [line for line in block if line]
    if len(block) > 1 and "," in block[-1]:
        city, _sep, state = block.pop().rpartition(",")
        data.city = city.strip() or None
        data.state = state.strip(" .") or None
    if block:
        data.street = block[0]
        data.street2 = " ".join(block[1:]) or None
    for key in ("street", "street2", "zip", "city", "state"):
        if getattr(data, key):
            data.confidence[key] = 0.7 if key != "zip" else 0.8


def _parse_birth_text(lines):
    """Fecha de nacimiento impresa (no la de la CURP)."""
    for index, line in enumerate(lines):
        rest = _after_label(line, LABEL_BIRTH)
        if rest is None:
            continue
        for text in (rest, lines[index + 1] if index + 1 < len(lines) else ""):
            found = _DATE_RE.search(text.upper().translate(_TO_DIGIT))
            if found:
                day, month, year = map(int, found.groups())
                return _valid_date(year, month, day)
    return None


def _parse_sex_text(lines):
    for line in lines:
        rest = _after_label(line, LABEL_SEX)
        if rest:
            letter = rest.strip().upper()[:1]
            if letter in ("H", "M"):
                return letter
    return None


def _year_after(pattern, text):
    found = re.search(pattern, text)
    return int(found.group(1)) if found else None


def parse_front(text):
    """Interpreta el texto OCR del frente de una INE."""
    lines = _lines(text)
    flat = _norm(" ".join(lines))
    data = IneData()

    _parse_names(lines, data)
    _parse_address(lines, data)

    curp = _find_curp(lines)
    if curp:
        data.curp = curp["curp"]
        data.birth_state_code = curp["state_code"]
        data.confidence["curp"] = 1.0 if curp["check_ok"] else 0.5
        if not curp["check_ok"]:
            data.warnings.append(
                "El dígito verificador de la CURP no coincide: revisa la CURP."
            )
        if curp["state_code"] not in CURP_STATES:
            data.warnings.append("La entidad de la CURP no es válida: revisa la CURP.")

    data.elector_key = _find_elector_key(lines)
    if data.elector_key:
        data.confidence["elector_key"] = 0.8

    # Fecha de nacimiento y sexo: la CURP manda si es confiable.
    printed_birth = _parse_birth_text(lines)
    printed_sex = _parse_sex_text(lines)
    if curp and curp["check_ok"]:
        data.birth_date, data.confidence["birth_date"] = curp["birth_date"], 1.0
        data.sex = curp["sex"] or printed_sex
    else:
        data.birth_date = printed_birth or (curp and curp["birth_date"]) or None
        data.sex = printed_sex or (curp and curp["sex"]) or None
        if data.birth_date:
            data.confidence["birth_date"] = 0.7 if printed_birth else 0.5
    if data.sex:
        data.confidence["sex"] = 1.0 if curp and curp["check_ok"] else 0.7
    if curp and printed_birth and printed_birth != curp["birth_date"]:
        data.warnings.append(
            "La fecha de nacimiento impresa no coincide con la de la CURP."
        )
    if curp and printed_sex and curp["sex"] and printed_sex != curp["sex"]:
        data.warnings.append("El sexo impreso no coincide con el de la CURP.")

    section = re.search(r"SECC\w{0,3}N\s*[:.]?\s*(\d{4})", flat)
    data.section = section.group(1) if section else None
    data.registration_year = _year_after(r"REGISTRO\s*[:.]?\s*(\d{4})", flat)
    data.emission_year = _year_after(r"EMIS\w{0,4}N\s*[:.]?\s*(\d{4})", flat)
    data.validity_year = _year_after(r"VIGENCIA\s*[:.]?\s*(?:\d{4}\s*[-–]\s*)?(\d{4})", flat)
    for key in ("section", "registration_year", "emission_year", "validity_year"):
        if getattr(data, key):
            data.confidence[key] = 0.8
    return data


# --------------------------------------------------------------------------
# Reverso de la INE (MRZ)
# --------------------------------------------------------------------------

def _mrz_value(char):
    if char.isdigit():
        return int(char)
    return 0 if char == "<" else ord(char) - 55


def mrz_check_digit(field_text):
    """Dígito verificador OACI (pesos 7-3-1) de un campo del MRZ."""
    weights = (7, 3, 1)
    return sum(_mrz_value(c) * weights[i % 3] for i, c in enumerate(field_text)) % 10


def _clean_mrz(line):
    cleaned = re.sub(r"\s+", "", line.upper())
    return cleaned.translate(str.maketrans({"«": "<", "‹": "<", "‘": "<", "(": "<", "{": "<", "[": "<"}))


def _mrz_digits(text):
    return text.translate(_TO_DIGIT)


def _mrz_field(raw_field, raw_check, century_for):
    """Lee un campo de fecha del MRZ. Devuelve ``(date, verificado)``."""
    digits = _mrz_digits(raw_field)
    check = _mrz_digits(raw_check)
    if not (digits.isdigit() and check.isdigit()):
        return None, False
    year = century_for(int(digits[:2]))
    parsed = _valid_date(year, int(digits[2:4]), int(digits[4:6]))
    return parsed, parsed is not None and mrz_check_digit(digits) == int(check)


def parse_back(text, today=None):
    """Interpreta el texto OCR del reverso de una INE (zona MRZ)."""
    today = today or date.today()
    data = IneData()
    lines = [_clean_mrz(line) for line in _lines(text)]
    for index, line in enumerate(lines):
        if _MRZ_LINE2_RE.match(line):
            break
    else:
        return data
    line2 = line.ljust(30, "<")
    line3 = lines[index + 1] if index + 1 < len(lines) else ""

    def birth_century(two_digits):
        return 2000 + two_digits if two_digits <= today.year % 100 else 1900 + two_digits

    birth, birth_ok = _mrz_field(line2[0:6], line2[6], birth_century)
    expiry, expiry_ok = _mrz_field(line2[8:14], line2[14], lambda y: 2000 + y)
    if birth:
        data.birth_date = birth
        data.confidence["birth_date"] = 1.0 if birth_ok else 0.5
    sex = line2[7]
    data.sex = {"H": "H", "M": "M", "F": "M"}.get(sex)
    if data.sex:
        data.confidence["sex"] = 0.8
    if expiry:
        data.validity_year = expiry.year
        data.confidence["validity_year"] = 1.0 if expiry_ok else 0.5
    if not birth_ok or not expiry_ok:
        data.warnings.append(
            "Algún dígito verificador del reverso no coincide: revisa las fechas."
        )

    # Línea de nombres: «PATERNO<MATERNO<<NOMBRES<<<<».
    name_line = re.sub(r"[K<]{3,}$", "", re.sub(r"[^A-Z<]", "", line3))
    if "<<" in name_line:
        surnames, _sep, given = name_line.partition("<<")
        parts = [part for part in surnames.split("<") if part]
        given_names = " ".join(part for part in given.split("<") if part)
        if parts and given_names:
            data.paternal_surname = parts[0]
            data.maternal_surname = " ".join(parts[1:]) or None
            data.first_name = given_names
            for key in ("first_name", "paternal_surname", "maternal_surname"):
                if getattr(data, key):
                    data.confidence[key] = 0.7
    elif name_line:
        data.warnings.append("No se pudieron separar los apellidos y el nombre del reverso.")
    return data


# --------------------------------------------------------------------------
# Unión de frente y reverso
# --------------------------------------------------------------------------

def _same_name(a, b):
    squash = lambda text: re.sub(r"[^A-Z]", "", _strip_accents(text.upper()))  # noqa: E731
    return squash(a) == squash(b)


def merge(front, back):
    """Combina frente y reverso: el frente manda (conserva acentos y Ñ) y el
    reverso completa lo que falte y detecta inconsistencias."""
    merged = IneData(**{k: (list(v) if isinstance(v, list) else dict(v) if isinstance(v, dict) else v)
                        for k, v in front.__dict__.items()})
    merged.warnings = list(front.warnings) + [
        w for w in back.warnings if w not in front.warnings
    ]

    for key in ("first_name", "paternal_surname", "maternal_surname"):
        own, other = getattr(front, key), getattr(back, key)
        if other and not own:
            setattr(merged, key, other)
            merged.confidence[key] = back.confidence.get(key, 0.5)
        elif own and other and not _same_name(own, other):
            merged.warnings.append(
                "El nombre del frente y el del reverso no coinciden (%s)." % key
            )
    for key, label in (("birth_date", "la fecha de nacimiento"), ("sex", "el sexo")):
        own, other = getattr(front, key), getattr(back, key)
        if other and not own:
            setattr(merged, key, other)
            merged.confidence[key] = back.confidence.get(key, 0.5)
        elif own and other and own != other:
            merged.warnings.append("No coinciden %s del frente y del reverso." % label)
    if back.validity_year and not front.validity_year:
        merged.validity_year = back.validity_year
        merged.confidence["validity_year"] = back.confidence.get("validity_year", 0.5)
    elif back.validity_year and front.validity_year != back.validity_year:
        merged.warnings.append("No coincide la vigencia del frente con la del reverso.")
    return merged


def parse_ine(front_text, back_text=None, today=None):
    """Interpreta una INE a partir del texto OCR de su frente y, si se tiene,
    de su reverso."""
    front = parse_front(front_text)
    if not back_text:
        return front
    return merge(front, parse_back(back_text, today=today))
