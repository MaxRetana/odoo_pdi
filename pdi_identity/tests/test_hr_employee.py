# Part of odoo_pdi. See LICENSE file for full copyright and licensing details.
import base64
import io
from datetime import date
from unittest.mock import patch

from PIL import Image

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, new_test_user, tagged

from .test_ine_parser import BACK_A, FRONT_A


def _image_b64():
    buffer = io.BytesIO()
    Image.new("RGB", (400, 250), "white").save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue())


@tagged("post_install", "-at_install")
class TestHrEmployeeIdentity(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Scan = self.env["pdi.identity.scan"]
        self.ocr_class = type(self.env["pdi.ocr.service"])

    def _scan(self, wizard, *texts):
        with patch.object(self.ocr_class, "read_text", side_effect=list(texts)):
            wizard.action_scan()

    def test_create_an_employee_from_the_ine(self):
        wizard = self.Scan.create({
            "target_model": "hr.employee",
            "front_image": _image_b64(), "back_image": _image_b64(),
        })
        self._scan(wizard, FRONT_A, BACK_A)
        action = wizard.action_apply()
        employee = self.env["hr.employee"].browse(action["res_id"])
        self.assertEqual(action["res_model"], "hr.employee")
        self.assertEqual(employee.name, "Juan Carlos Garcia Lopez")
        self.assertEqual(employee.birthday, date(1980, 1, 1))
        self.assertEqual(employee.sex, "male")
        self.assertEqual(employee.identification_id, "GALJ800101HJCRPN05")
        self.assertEqual(employee.country_id.code, "MX")
        self.assertEqual(employee.place_of_birth, "Jalisco")
        self.assertEqual(employee.country_of_birth.code, "MX")
        self.assertEqual(employee.private_street, "C Roble 123")
        self.assertEqual(employee.private_street2, "Col Centro")
        self.assertEqual(employee.private_zip, "44100")
        self.assertEqual(employee.private_city, "Guadalajara")
        self.assertEqual(employee.private_state_id.code, "JAL")
        self.assertEqual(employee.private_country_id.code, "MX")
        self.assertEqual(employee.pdi_curp, "GALJ800101HJCRPN05")
        self.assertEqual(employee.pdi_elector_key, "GRLPJN80010114H100")
        self.assertEqual(employee.pdi_ine_validity_year, 2029)

    def test_complete_an_existing_employee_without_erasing_data(self):
        employee = self.env["hr.employee"].create({
            "name": "Pendiente", "work_email": "juan@example.com", "private_phone": "5551234567",
        })
        action = employee.action_pdi_scan_identity()
        self.assertEqual(action["context"]["default_target_model"], "hr.employee")
        self.assertEqual(action["context"]["default_target_res_id"], employee.id)
        wizard = self.Scan.with_context(**action["context"]).create({"front_image": _image_b64()})
        self._scan(wizard, FRONT_A)
        wizard.action_apply()
        self.assertEqual(employee.name, "Juan Carlos Garcia Lopez")
        self.assertEqual(employee.work_email, "juan@example.com")
        self.assertEqual(employee.private_phone, "5551234567")
        self.assertEqual(employee.pdi_curp, "GALJ800101HJCRPN05")

    def test_foreign_born_has_no_birth_state(self):
        data = {"full_name": "Andres Perez", "curp": "PEXA010705HNEXXNA9", "birth_state_id": False}
        vals = self.env["hr.employee"]._pdi_identity_prepare_vals(data)
        self.assertFalse(vals["place_of_birth"])
        self.assertFalse(vals["country_of_birth"])

    def test_sensitive_fields_are_hidden_from_users_without_the_group(self):
        employee = self.env["hr.employee"].create({"name": "Ana", "pdi_curp": "GALJ800101HJCRPN05"})
        hr_only = new_test_user(self.env, login="pdi_hr", groups="base.group_user,hr.group_hr_user")
        scanner = new_test_user(
            self.env, login="pdi_hr_scanner",
            groups="base.group_user,hr.group_hr_user,pdi_identity.group_pdi_identity_user",
        )
        with self.assertRaises(AccessError):
            employee.with_user(hr_only).read(["pdi_curp"])
        self.assertEqual(
            employee.with_user(scanner).read(["pdi_curp"])[0]["pdi_curp"], "GALJ800101HJCRPN05"
        )

    def test_buttons_are_only_in_the_views_of_scanner_users(self):
        hr_only = new_test_user(self.env, login="pdi_hr2", groups="base.group_user,hr.group_hr_user")
        scanner = new_test_user(
            self.env, login="pdi_hr_scanner2",
            groups="base.group_user,hr.group_hr_user,pdi_identity.group_pdi_identity_user",
        )
        employee = self.env["hr.employee"]
        form = employee.with_user(scanner).get_view(view_type="form")["arch"]
        listing = employee.with_user(scanner).get_view(view_type="list")["arch"]
        self.assertIn("action_pdi_scan_identity", form)
        self.assertIn("pdi_elector_key", form)
        self.assertIn("action_pdi_create_from_identity", listing)
        plain_form = employee.with_user(hr_only).get_view(view_type="form")["arch"]
        plain_list = employee.with_user(hr_only).get_view(view_type="list")["arch"]
        self.assertNotIn("action_pdi_scan_identity", plain_form)
        self.assertNotIn("pdi_elector_key", plain_form)
        self.assertNotIn("action_pdi_create_from_identity", plain_list)
