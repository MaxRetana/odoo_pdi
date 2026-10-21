# Part of odoo_pdi. See LICENSE file for full copyright and licensing details.
import base64
import io
from datetime import date
from unittest.mock import patch

from PIL import Image

from odoo.exceptions import UserError
from odoo.tests import Form
from odoo.tests.common import TransactionCase, tagged

from .test_ine_parser import BACK_A, FRONT_A


def _image_b64():
    buffer = io.BytesIO()
    Image.new("RGB", (400, 250), "white").save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue())


@tagged("post_install", "-at_install")
class TestIdentityScan(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Scan = self.env["pdi.identity.scan"]
        self.service_class = type(self.env["pdi.ocr.service"])

    def _wizard(self, **vals):
        values = {"target_model": "res.partner", "front_image": _image_b64()}
        values.update(vals)
        return self.Scan.create(values)

    def _scan(self, wizard, *texts):
        with patch.object(self.service_class, "read_text", side_effect=list(texts)):
            return wizard.action_scan()

    def test_scan_fills_the_editable_fields(self):
        wizard = self._wizard(back_image=_image_b64())
        action = self._scan(wizard, FRONT_A, BACK_A)
        self.assertEqual(action["res_id"], wizard.id)
        self.assertEqual(action["target"], "new")
        self.assertEqual(wizard.step, "review")
        self.assertEqual(wizard.first_name, "Juan Carlos")
        self.assertEqual(wizard.paternal_surname, "Garcia")
        self.assertEqual(wizard.maternal_surname, "Lopez")
        self.assertEqual(wizard.curp, "GALJ800101HJCRPN05")
        self.assertEqual(wizard.elector_key, "GRLPJN80010114H100")
        self.assertEqual(wizard.birth_date, date(1980, 1, 1))
        self.assertEqual(wizard.gender, "male")
        self.assertEqual(wizard.street, "C Roble 123")
        self.assertEqual(wizard.street2, "Col Centro")
        self.assertEqual(wizard.zip, "44100")
        self.assertEqual(wizard.city, "Guadalajara")
        self.assertEqual(wizard.country_id, self.env.ref("base.mx"))
        self.assertEqual(wizard.state_id.code, "JAL")
        self.assertEqual(wizard.birth_state_id.code, "JAL")
        self.assertEqual(wizard.validity_year, 2029)
        self.assertFalse(wizard.warnings)

    def test_scan_only_front(self):
        wizard = self._wizard()
        self._scan(wizard, FRONT_A)
        self.assertEqual(wizard.curp, "GALJ800101HJCRPN05")

    def test_scan_requires_the_front_image(self):
        wizard = self._wizard(front_image=False)
        with self.assertRaises(UserError):
            wizard.action_scan()

    def test_scan_of_an_unreadable_image_raises(self):
        wizard = self._wizard()
        with self.assertRaisesRegex(UserError, "No se pudieron leer"):
            self._scan(wizard, "texto sin datos de ninguna credencial")

    def test_warnings_are_shown(self):
        wizard = self._wizard()
        self._scan(wizard, FRONT_A.replace("HJCRPN05", "HJCRPN06"))
        self.assertIn("verificador", wizard.warnings)

    def test_back_returns_to_the_first_step(self):
        wizard = self._wizard()
        self._scan(wizard, FRONT_A)
        action = wizard.action_back()
        self.assertEqual(wizard.step, "draft")
        self.assertEqual(action["res_id"], wizard.id)

    def test_get_data_uses_the_reviewed_values(self):
        wizard = self._wizard()
        self._scan(wizard, FRONT_A)
        wizard.write({"first_name": "Juan", "curp": " galj800101hjcrpn05 "})
        data = wizard._get_data()
        self.assertEqual(data["full_name"], "Juan Garcia Lopez")
        self.assertEqual(data["curp"], "GALJ800101HJCRPN05")

    # -- aplicar: se simula el mapeo que implementa cada modelo destino para
    # -- probar el asistente de forma aislada (el mapeo real de ``res.partner``
    # -- se prueba en ``test_res_partner``).

    def _patch_prepare(self, captured):
        def prepare(record, data):
            captured.append(data)
            return {
                "name": data["full_name"], "street": data["street"],
                "zip": data["zip"], "comment": False,
            }
        return patch.object(
            type(self.env["res.partner"]), "_pdi_identity_prepare_vals",
            prepare, create=True,
        )

    def test_apply_creates_the_record(self):
        wizard = self._wizard(back_image=_image_b64())
        self._scan(wizard, FRONT_A, BACK_A)
        captured = []
        with self._patch_prepare(captured):
            action = wizard.action_apply()
        partner = self.env["res.partner"].browse(action["res_id"])
        self.assertEqual(partner.name, "Juan Carlos Garcia Lopez")
        self.assertEqual(partner.street, "C Roble 123")
        self.assertEqual(captured[0]["curp"], "GALJ800101HJCRPN05")
        self.assertEqual(action["res_model"], "res.partner")

    def test_apply_completes_an_existing_record_without_erasing_data(self):
        partner = self.env["res.partner"].create({"name": "Pendiente", "street": "Calle vieja"})
        wizard = self._wizard(target_res_id=partner.id)
        self._scan(wizard, FRONT_A)
        wizard.write({"street": False})  # el OCR no leyó la calle
        with self._patch_prepare([]):
            wizard.action_apply()
        self.assertEqual(partner.name, "Juan Carlos Garcia Lopez")
        self.assertEqual(partner.street, "Calle vieja")

    def test_apply_requires_a_name_or_curp(self):
        wizard = self._wizard()
        with self._patch_prepare([]), self.assertRaises(UserError):
            wizard.action_apply()

    def test_images_are_cleared_after_applying(self):
        wizard = self._wizard(back_image=_image_b64())
        self._scan(wizard, FRONT_A, BACK_A)
        with self._patch_prepare([]):
            action = wizard.action_apply()
        self.assertFalse(wizard.front_image)
        self.assertFalse(wizard.back_image)
        attachments = self.env["ir.attachment"].search([
            ("res_model", "=", "res.partner"), ("res_id", "=", action["res_id"]),
        ])
        self.assertFalse(attachments)

    def test_images_are_attached_when_the_setting_is_enabled(self):
        self.env["ir.config_parameter"].sudo().set_param("pdi_identity.keep_images", "True")
        wizard = self._wizard(back_image=_image_b64())
        self._scan(wizard, FRONT_A, BACK_A)
        with self._patch_prepare([]):
            action = wizard.action_apply()
        attachments = self.env["ir.attachment"].search([
            ("res_model", "=", "res.partner"), ("res_id", "=", action["res_id"]),
        ])
        self.assertEqual(sorted(attachments.mapped("name")), ["INE (frente)", "INE (reverso)"])

    def test_get_action_sets_the_target_in_the_context(self):
        action = self.Scan._get_action("hr.employee", 7)
        self.assertEqual(action["context"]["default_target_model"], "hr.employee")
        self.assertEqual(action["context"]["default_target_res_id"], 7)
        self.assertEqual(action["target"], "new")

    def test_form_view_flow(self):
        """El asistente se puede llenar y leer desde su vista, como lo haría un usuario."""
        action = self.Scan._get_action("res.partner")
        with Form(self.Scan.with_context(**action["context"])) as form:
            self.assertEqual(form.target_model, "res.partner")
            self.assertEqual(form.step, "draft")
            form.front_image = _image_b64().decode()
        wizard = form.save()
        self._scan(wizard, FRONT_A)
        with Form(wizard) as form:
            self.assertEqual(form.step, "review")
            form.first_name = "Juan"
            self.assertEqual(form.curp, "GALJ800101HJCRPN05")
        self.assertEqual(wizard.first_name, "Juan")
