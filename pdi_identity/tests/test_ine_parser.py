# Part of odoo_pdi. See LICENSE file for full copyright and licensing details.
"""Pruebas del parser de INE.

Todos los datos son ficticios: las CURP tienen dígito verificador válido, pero
no pertenecen a ninguna persona.
"""
import json
from datetime import date

from odoo.tests.common import BaseCase, tagged

from ..tools import ine_parser as ine

TODAY = date(2026, 10, 21)

FRONT_A = """
INSTITUTO NACIONAL ELECTORAL
MEXICO
CREDENCIAL PARA VOTAR
NOMBRE
GARCIA
LOPEZ
JUAN CARLOS
DOMICILIO
C ROBLE 123
COL CENTRO 44100
GUADALAJARA, JAL.
CLAVE DE ELECTOR GRLPJN80010114H100
CURP GALJ800101HJCRPN05
FECHA DE NACIMIENTO
01/01/1980
SEXO H
AÑO DE REGISTRO 2000 01
ESTADO 14 MUNICIPIO 039
SECCION 0123 LOCALIDAD 0001
EMISION 2019 VIGENCIA 2029
"""

# El mismo frente, con los errores típicos del OCR.
FRONT_A_NOISY = """
INSTITUT0 NACIONAL ELECTORAL
CREDENCIAL PARA V0TAR
| NOMBRF
GARCIA
LOPEZ
JUAN CARL0S
DOMICILI0
C ROBLE 123
C0L CENTRO 44100
GUADALAJARA, JAL.
CLAVE DE ELECT0R GRLPJN8OO1O114H1OO
CURP GALJ8OO1O1HJCRPN05
FECHA DE NACIMIENT0
01/O1/1980
SEXO H
SECCI0N 0123
"""

FRONT_B = """
NOMBRE
ROMERO
ORTIZ
MARIA FERNANDA
DOMICILIO
AV UNIVERSIDAD 1000 INT 5
COL NARVARTE 03020
CIUDAD DE MEXICO, CDMX
CLAVE DE ELECTOR RMRTMR95112309M200
CURP RORM951123MDFDDR04
FECHA DE NACIMIENTO 23/11/1995
SEXO M
SECCION 4567
VIGENCIA 2020 - 2030
"""

FRONT_NTILDE = """
NOMBRE
MUÑOZ
PEÑA
JOSE ANGEL
DOMICILIO
C HIDALGO 5
TLAXCALA, TLAX.
CURP MUPJ900415HTLXXS06
"""

FRONT_TWO_LINES = """
NOMBRE
PEREZ
ANDRES
DOMICILIO
C LUNA 9
CURP PEXA010705HNEXXNA9
"""

BACK_A = """
IDMEX1930123401<<0123456789012
8001014H2912316MEX<02<<<<<<<<4
GARCIA<LOPEZ<<JUAN<CARLOS<<<<<
"""

BACK_A_NOISY = """
IDMEX1930123401<<0123456789012
800101 4H2912316MEX<O2<<<<<<<<4
GARCIA<LOPEZ<<JUAN<CARLOSKKKKK
"""

BACK_B = """
IDMEX1930123402<<0123456789012
9511235M3106305MEX<08<<<<<<<<2
ROMERO<ORTIZ<<MARIA<FERNANDA<<
"""

BACK_NTILDE = """
8
9004159H3010150MEX<01<<<<<<<<3
MUNOZ<PENA<<JOSE<ANGEL<<<<<<<<
"""


@tagged("post_install", "-at_install")
class TestCurp(BaseCase):

    def test_check_digit(self):
        self.assertEqual(ine.curp_check_digit("GALJ800101HJCRPN0"), 5)
        self.assertEqual(ine.curp_check_digit("MUPJ900415HTLXXS0"), 6)

    def test_valid_curp(self):
        parsed = ine.parse_curp("GALJ800101HJCRPN05")
        self.assertEqual(parsed["curp"], "GALJ800101HJCRPN05")
        self.assertEqual(parsed["birth_date"], date(1980, 1, 1))
        self.assertEqual(parsed["sex"], "H")
        self.assertEqual(parsed["state_code"], "JC")
        self.assertTrue(parsed["check_ok"])
        self.assertEqual(parsed["fixes"], 0)

    def test_ocr_errors_are_corrected_by_position(self):
        parsed = ine.parse_curp("GALJ8OO1O1HJCRPN05")
        self.assertEqual(parsed["curp"], "GALJ800101HJCRPN05")
        self.assertEqual(parsed["fixes"], 3)
        self.assertTrue(parsed["check_ok"])

    def test_wrong_check_digit_is_detected(self):
        parsed = ine.parse_curp("GALJ800101HJCRPN06")
        self.assertFalse(parsed["check_ok"])

    def test_century_comes_from_the_homoclave(self):
        self.assertEqual(ine.parse_curp("PEXA010705HNEXXNA9")["birth_date"], date(2001, 7, 5))
        self.assertEqual(ine.parse_curp("RORM951123MDFDDR04")["birth_date"], date(1995, 11, 23))

    def test_invalid_structure_returns_none(self):
        self.assertIsNone(ine.parse_curp("ESTO NO ES UNA CURP"))
        self.assertIsNone(ine.parse_curp("GALJ801301HJCRPN05"))  # mes 13
        self.assertIsNone(ine.parse_curp(""))

    def test_elector_key(self):
        self.assertEqual(ine.parse_elector_key("GRLPJN80010114H100"), "GRLPJN80010114H100")
        self.assertEqual(ine.parse_elector_key("GRLPJN8OO1O114H1OO"), "GRLPJN80010114H100")
        self.assertIsNone(ine.parse_elector_key("GRLPJN80130114H100"))  # mes 13
        self.assertIsNone(ine.parse_elector_key("corta"))


@tagged("post_install", "-at_install")
class TestParseFront(BaseCase):

    def test_clean_front(self):
        data = ine.parse_front(FRONT_A)
        self.assertEqual(data.paternal_surname, "GARCIA")
        self.assertEqual(data.maternal_surname, "LOPEZ")
        self.assertEqual(data.first_name, "JUAN CARLOS")
        self.assertEqual(data.full_name, "JUAN CARLOS GARCIA LOPEZ")
        self.assertEqual(data.curp, "GALJ800101HJCRPN05")
        self.assertEqual(data.elector_key, "GRLPJN80010114H100")
        self.assertEqual(data.birth_date, date(1980, 1, 1))
        self.assertEqual(data.sex, "H")
        self.assertEqual(data.gender, "male")
        self.assertEqual(data.birth_state_code, "JC")
        self.assertEqual(data.street, "C ROBLE 123")
        self.assertEqual(data.street2, "COL CENTRO")
        self.assertEqual(data.zip, "44100")
        self.assertEqual(data.city, "GUADALAJARA")
        self.assertEqual(data.state, "JAL")
        self.assertEqual(data.section, "0123")
        self.assertEqual(data.registration_year, 2000)
        self.assertEqual(data.emission_year, 2019)
        self.assertEqual(data.validity_year, 2029)
        self.assertEqual(data.confidence["curp"], 1.0)
        self.assertEqual(data.warnings, [])

    def test_noisy_front_is_still_read(self):
        data = ine.parse_front(FRONT_A_NOISY)
        self.assertEqual(data.full_name, "JUAN CARLOS GARCIA LOPEZ")
        self.assertEqual(data.curp, "GALJ800101HJCRPN05")
        self.assertEqual(data.elector_key, "GRLPJN80010114H100")
        self.assertEqual(data.birth_date, date(1980, 1, 1))
        self.assertEqual(data.zip, "44100")
        self.assertEqual(data.city, "GUADALAJARA")
        self.assertEqual(data.section, "0123")

    def test_woman_with_inline_birth_date_and_validity_range(self):
        data = ine.parse_front(FRONT_B)
        self.assertEqual(data.full_name, "MARIA FERNANDA ROMERO ORTIZ")
        self.assertEqual(data.birth_date, date(1995, 11, 23))
        self.assertEqual(data.sex, "M")
        self.assertEqual(data.gender, "female")
        self.assertEqual(data.birth_state_code, "DF")
        self.assertEqual(data.street, "AV UNIVERSIDAD 1000 INT 5")
        self.assertEqual(data.zip, "03020")
        self.assertEqual(data.city, "CIUDAD DE MEXICO")
        self.assertEqual(data.state, "CDMX")
        self.assertEqual(data.validity_year, 2030)

    def test_enye_is_kept_in_the_name(self):
        data = ine.parse_front(FRONT_NTILDE)
        self.assertEqual(data.paternal_surname, "MUÑOZ")
        self.assertEqual(data.maternal_surname, "PEÑA")
        self.assertEqual(data.first_name, "JOSE ANGEL")
        self.assertEqual(data.birth_date, date(1990, 4, 15))

    def test_two_name_lines_warn_the_user(self):
        data = ine.parse_front(FRONT_TWO_LINES)
        self.assertEqual(data.paternal_surname, "PEREZ")
        self.assertIsNone(data.maternal_surname)
        self.assertEqual(data.first_name, "ANDRES")
        self.assertEqual(data.birth_date, date(2001, 7, 5))
        self.assertTrue(any("dos líneas" in w for w in data.warnings))

    def test_bad_check_digit_lowers_confidence_and_warns(self):
        data = ine.parse_front(FRONT_A.replace("HJCRPN05", "HJCRPN06"))
        self.assertEqual(data.confidence["curp"], 0.5)
        self.assertTrue(any("verificador" in w for w in data.warnings))

    def test_printed_birth_date_that_disagrees_with_the_curp_warns(self):
        data = ine.parse_front(FRONT_A.replace("01/01/1980", "02/01/1980"))
        self.assertEqual(data.birth_date, date(1980, 1, 1))  # manda la CURP
        self.assertTrue(any("fecha de nacimiento" in w for w in data.warnings))

    def test_without_curp_the_printed_data_is_used(self):
        text = "\n".join(
            line for line in FRONT_A.splitlines() if not line.startswith("CURP")
        )
        data = ine.parse_front(text)
        self.assertIsNone(data.curp)
        self.assertEqual(data.birth_date, date(1980, 1, 1))
        self.assertEqual(data.sex, "H")
        self.assertEqual(data.confidence["birth_date"], 0.7)

    def test_empty_or_unrelated_text_gives_empty_data(self):
        for text in ("", None, "hola mundo\n12345\n"):
            data = ine.parse_front(text)
            self.assertIsNone(data.curp)
            self.assertEqual(data.full_name, "")

    def test_result_is_json_serializable(self):
        payload = json.dumps(ine.parse_front(FRONT_A).to_dict())
        self.assertIn("1980-01-01", payload)


@tagged("post_install", "-at_install")
class TestParseBack(BaseCase):

    def test_mrz(self):
        data = ine.parse_back(BACK_A, today=TODAY)
        self.assertEqual(data.paternal_surname, "GARCIA")
        self.assertEqual(data.maternal_surname, "LOPEZ")
        self.assertEqual(data.first_name, "JUAN CARLOS")
        self.assertEqual(data.birth_date, date(1980, 1, 1))
        self.assertEqual(data.sex, "H")
        self.assertEqual(data.validity_year, 2029)
        self.assertEqual(data.confidence["birth_date"], 1.0)
        self.assertEqual(data.warnings, [])

    def test_mrz_with_ocr_noise(self):
        data = ine.parse_back(BACK_A_NOISY, today=TODAY)
        self.assertEqual(data.birth_date, date(1980, 1, 1))
        self.assertEqual(data.validity_year, 2029)
        self.assertEqual(data.first_name, "JUAN CARLOS")
        self.assertEqual(data.confidence["birth_date"], 1.0)

    def test_mrz_century_depends_on_today(self):
        data = ine.parse_back("0107057H3301018MEX<02<<<<<<<<0\nPEREZ<<ANDRES<<<<<<<<<<<", today=TODAY)
        self.assertEqual(data.birth_date, date(2001, 7, 5))
        self.assertEqual(data.maternal_surname, None)

    def test_wrong_check_digit_warns(self):
        data = ine.parse_back(BACK_A.replace("8001014H", "8001015H"), today=TODAY)
        self.assertEqual(data.confidence["birth_date"], 0.5)
        self.assertTrue(any("verificador" in w for w in data.warnings))

    def test_text_without_mrz_gives_empty_data(self):
        data = ine.parse_back("texto cualquiera\notra línea", today=TODAY)
        self.assertIsNone(data.birth_date)
        self.assertIsNone(data.first_name)


@tagged("post_install", "-at_install")
class TestParseIne(BaseCase):

    def test_front_and_back_agree(self):
        data = ine.parse_ine(FRONT_A, BACK_A, today=TODAY)
        self.assertEqual(data.full_name, "JUAN CARLOS GARCIA LOPEZ")
        self.assertEqual(data.warnings, [])

    def test_front_keeps_the_enye_and_back_does_not_conflict(self):
        data = ine.parse_ine(FRONT_NTILDE, BACK_NTILDE, today=TODAY)
        self.assertEqual(data.paternal_surname, "MUÑOZ")
        self.assertEqual(data.warnings, [])

    def test_back_fills_what_the_front_lacks(self):
        data = ine.parse_ine("sin datos útiles", BACK_B, today=TODAY)
        self.assertEqual(data.full_name, "MARIA FERNANDA ROMERO ORTIZ")
        self.assertEqual(data.birth_date, date(1995, 11, 23))
        self.assertEqual(data.sex, "M")
        self.assertEqual(data.validity_year, 2031)

    def test_disagreements_between_sides_are_reported(self):
        data = ine.parse_ine(FRONT_A, BACK_B, today=TODAY)
        warnings = " ".join(data.warnings)
        self.assertIn("nombre", warnings)
        self.assertIn("fecha de nacimiento", warnings)
        self.assertIn("sexo", warnings)
        self.assertIn("vigencia", warnings)
        # El frente manda: los datos no se sobrescriben.
        self.assertEqual(data.first_name, "JUAN CARLOS")

    def test_without_back_returns_the_front(self):
        self.assertEqual(
            ine.parse_ine(FRONT_A).to_dict(), ine.parse_front(FRONT_A).to_dict()
        )
