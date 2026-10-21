# Part of odoo_pdi. See LICENSE file for full copyright and licensing details.
from odoo.tests.common import BaseCase, tagged

from ..tools import ine_parser, mx_states


@tagged("post_install", "-at_install")
class TestMxStates(BaseCase):

    def test_address_abbreviations(self):
        cases = {
            "JAL.": "JAL", "CDMX": "CMX", "D.F.": "CMX", "N.L.": "NLE",
            "TAMPS.": "TAM", "Q. ROO": "ROO", "QRO.": "QUE", "S.L.P.": "SLP",
            "B.C.": "BCN", "B.C.S.": "BCS", "AGS.": "AGU", "TLAX.": "TLA",
            "MICH.": "MIC", "Yucatán": "YUC", "Estado de México": "MEX",
        }
        for text, code in cases.items():
            self.assertEqual(mx_states.odoo_state_code(text), code, text)

    def test_unknown_state(self):
        self.assertIsNone(mx_states.odoo_state_code("XYZ"))
        self.assertIsNone(mx_states.odoo_state_code(None))
        self.assertIsNone(mx_states.odoo_state_code(""))

    def test_curp_states_cover_every_valid_state_code(self):
        for code in ine_parser.CURP_STATES:
            self.assertIn(code, mx_states.CURP_STATE_TO_ODOO)
        self.assertEqual(mx_states.odoo_state_code_from_curp("JC"), "JAL")
        self.assertEqual(mx_states.odoo_state_code_from_curp("df"), "CMX")
        self.assertIsNone(mx_states.odoo_state_code_from_curp("NE"))
        self.assertIsNone(mx_states.odoo_state_code_from_curp(None))
