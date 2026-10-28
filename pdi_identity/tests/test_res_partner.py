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
class TestResPartnerIdentity(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Scan = self.env["pdi.identity.scan"]
        self.ocr_class = type(self.env["pdi.ocr.service"])

    def _scan(self, wizard, *texts):
        with patch.object(self.ocr_class, "read_text", side_effect=list(texts)):
            wizard.action_scan()

    def test_prepare_vals(self):
        data = {
            "full_name": "Juan Carlos Garcia Lopez", "curp": "GALJ800101HJCRPN05",
            "elector_key": "GRLPJN80010114H100", "validity_year": 2029,
            "street": "C Roble 123", "street2": "Col Centro", "zip": "44100",
            "city": "Guadalajara", "state_id": 1, "country_id": 2,
        }
        vals = self.env["res.partner"]._pdi_identity_prepare_vals(data)
        self.assertEqual(vals["name"], "Juan Carlos Garcia Lopez")
        self.assertEqual(vals["company_type"], "person")
        self.assertEqual(vals["pdi_curp"], "GALJ800101HJCRPN05")
        self.assertEqual(vals["pdi_elector_key"], "GRLPJN80010114H100")
        self.assertEqual(vals["pdi_ine_validity_year"], 2029)
        self.assertEqual(vals["street"], "C Roble 123")
        self.assertEqual(vals["state_id"], 1)

    def test_create_a_contact_from_the_ine(self):
        wizard = self.Scan.create({
            "target_model": "res.partner",
            "front_image": _image_b64(), "back_image": _image_b64(),
        })
        self._scan(wizard, FRONT_A, BACK_A)
        action = wizard.action_apply()
        partner = self.env["res.partner"].browse(action["res_id"])
        self.assertEqual(partner.name, "Juan Carlos Garcia Lopez")
        self.assertFalse(partner.is_company)
        self.assertEqual(partner.street, "C Roble 123")
        self.assertEqual(partner.street2, "Col Centro")
        self.assertEqual(partner.zip, "44100")
        self.assertEqual(partner.city, "Guadalajara")
        self.assertEqual(partner.state_id.code, "JAL")
        self.assertEqual(partner.country_id.code, "MX")
        self.assertEqual(partner.pdi_curp, "GALJ800101HJCRPN05")
        self.assertEqual(partner.pdi_elector_key, "GRLPJN80010114H100")
        self.assertEqual(partner.pdi_ine_validity_year, 2029)

    def test_complete_an_existing_contact(self):
        partner = self.env["res.partner"].create({
            "name": "Pendiente", "email": "juan@example.com",
        })
        action = partner.action_pdi_scan_identity()
        self.assertEqual(action["context"]["default_target_res_id"], partner.id)
        wizard = self.Scan.with_context(**action["context"]).create({
            "front_image": _image_b64(),
        })
        self._scan(wizard, FRONT_A)
        wizard.action_apply()
        self.assertEqual(partner.name, "Juan Carlos Garcia Lopez")
        self.assertEqual(partner.email, "juan@example.com")  # no se pierde
        self.assertEqual(partner.pdi_curp, "GALJ800101HJCRPN05")

    def test_create_from_list_keeps_the_default_values(self):
        action = self.env["res.partner"].with_context(
            default_supplier_rank=1, lang="en_US", search_default_x=1,
        ).action_pdi_create_from_identity()
        self.assertEqual(action["context"]["default_target_model"], "res.partner")
        self.assertEqual(action["context"]["default_supplier_rank"], 1)
        self.assertNotIn("lang", action["context"])
        self.assertNotIn("search_default_x", action["context"])

    def test_identity_fields_are_hidden_from_users_without_the_group(self):
        partner = self.env["res.partner"].create({"name": "Ana", "pdi_curp": "GALJ800101HJCRPN05"})
        plain = new_test_user(self.env, login="pdi_plain", groups="base.group_user")
        scanner = new_test_user(
            self.env, login="pdi_scanner",
            groups="base.group_user,pdi_identity.group_pdi_identity_user",
        )
        with self.assertRaises(AccessError):
            partner.with_user(plain).read(["pdi_curp"])
        self.assertEqual(
            partner.with_user(scanner).read(["pdi_curp"])[0]["pdi_curp"],
            "GALJ800101HJCRPN05",
        )

    def test_buttons_are_only_in_the_views_of_scanner_users(self):
        plain = new_test_user(self.env, login="pdi_plain2", groups="base.group_user")
        scanner = new_test_user(
            self.env, login="pdi_scanner2",
            groups="base.group_user,pdi_identity.group_pdi_identity_user",
        )
        partner = self.env["res.partner"]
        form = partner.with_user(scanner).get_view(view_type="form")["arch"]
        listing = partner.with_user(scanner).get_view(view_type="list")["arch"]
        self.assertIn("action_pdi_scan_identity", form)
        self.assertIn("pdi_curp", form)
        self.assertIn("action_pdi_create_from_identity", listing)
        plain_form = partner.with_user(plain).get_view(view_type="form")["arch"]
        plain_list = partner.with_user(plain).get_view(view_type="list")["arch"]
        self.assertNotIn("action_pdi_scan_identity", plain_form)
        self.assertNotIn("pdi_curp", plain_form)
        self.assertNotIn("action_pdi_create_from_identity", plain_list)

    def test_birth_date_is_not_lost_when_the_contact_is_created(self):
        wizard = self.Scan.create({"target_model": "res.partner", "front_image": _image_b64()})
        self._scan(wizard, FRONT_A)
        self.assertEqual(wizard.birth_date, date(1980, 1, 1))
        wizard.action_apply()
