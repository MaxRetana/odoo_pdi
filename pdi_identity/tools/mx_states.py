# Part of odoo_pdi. See LICENSE file for full copyright and licensing details.
"""Equivalencias de entidades federativas de México.

Los códigos de destino son los de ``res.country.state`` de Odoo (``JAL``,
``CMX``, ``NLE``...). Módulo de Python puro.
"""
import re
import unicodedata

# Clave de entidad de la CURP -> código de ``res.country.state``.
# ``NE`` (nacido en el extranjero) no corresponde a ningún estado.
CURP_STATE_TO_ODOO = {
    "AS": "AGU", "BC": "BCN", "BS": "BCS", "CC": "CAM", "CL": "COA",
    "CM": "COL", "CS": "CHP", "CH": "CHH", "DF": "CMX", "DG": "DUR",
    "GT": "GUA", "GR": "GRO", "HG": "HID", "JC": "JAL", "MC": "MEX",
    "MN": "MIC", "MS": "MOR", "NT": "NAY", "NL": "NLE", "OC": "OAX",
    "PL": "PUE", "QT": "QUE", "QR": "ROO", "SP": "SLP", "SL": "SIN",
    "SR": "SON", "TC": "TAB", "TS": "TAM", "TL": "TLA", "VZ": "VER",
    "YN": "YUC", "ZS": "ZAC", "NE": None,
}

# Abreviaturas con las que la INE imprime el estado del domicilio (sin puntos
# ni espacios) -> código de ``res.country.state``.
_ADDRESS_ALIASES = {
    "AGS": "AGU", "BC": "BCN", "BCS": "BCS", "CAMP": "CAM", "CHIH": "CHH",
    "CHIS": "CHP", "CDMX": "CMX", "DF": "CMX", "COAH": "COA", "COL": "COL",
    "DGO": "DUR", "GRO": "GRO", "GTO": "GUA", "HGO": "HID", "JAL": "JAL",
    "MEX": "MEX", "MICH": "MIC", "MOR": "MOR", "NAY": "NAY", "NL": "NLE",
    "OAX": "OAX", "PUE": "PUE", "QRO": "QUE", "QROO": "ROO", "SIN": "SIN",
    "SLP": "SLP", "SON": "SON", "TAB": "TAB", "TAMPS": "TAM", "TLAX": "TLA",
    "VER": "VER", "YUC": "YUC", "ZAC": "ZAC",
}

# Nombres completos (sin acentos, sin espacios) -> código.
_FULL_NAMES = {
    "AGUASCALIENTES": "AGU", "BAJACALIFORNIA": "BCN", "BAJACALIFORNIASUR": "BCS",
    "CAMPECHE": "CAM", "CHIHUAHUA": "CHH", "CHIAPAS": "CHP",
    "CIUDADDEMEXICO": "CMX", "DISTRITOFEDERAL": "CMX", "COAHUILA": "COA",
    "COLIMA": "COL", "DURANGO": "DUR", "GUERRERO": "GRO", "GUANAJUATO": "GUA",
    "HIDALGO": "HID", "JALISCO": "JAL", "ESTADODEMEXICO": "MEX",
    "MICHOACAN": "MIC", "MORELOS": "MOR", "NAYARIT": "NAY", "NUEVOLEON": "NLE",
    "OAXACA": "OAX", "PUEBLA": "PUE", "QUERETARO": "QUE", "QUINTANAROO": "ROO",
    "SINALOA": "SIN", "SANLUISPOTOSI": "SLP", "SONORA": "SON", "TABASCO": "TAB",
    "TAMAULIPAS": "TAM", "TLAXCALA": "TLA", "VERACRUZ": "VER", "YUCATAN": "YUC",
    "ZACATECAS": "ZAC",
}


def _squash(text):
    """Solo letras en mayúsculas y sin acentos."""
    decomposed = unicodedata.normalize("NFKD", (text or "").upper())
    return re.sub(r"[^A-Z]", "", "".join(c for c in decomposed if not unicodedata.combining(c)))


def odoo_state_code(text):
    """Código de ``res.country.state`` para el estado impreso en el domicilio
    de la INE (abreviatura o nombre), o ``None`` si no se reconoce."""
    key = _squash(text)
    return _ADDRESS_ALIASES.get(key) or _FULL_NAMES.get(key)


def odoo_state_code_from_curp(curp_state):
    """Código de ``res.country.state`` para la clave de entidad de la CURP."""
    return CURP_STATE_TO_ODOO.get((curp_state or "").upper())
