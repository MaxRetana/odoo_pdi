# Part of odoo_pdi. See LICENSE file for full copyright and licensing details.
import io
from unittest.mock import patch

from PIL import Image

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

from ..tools import ocr


def _png_bytes():
    buffer = io.BytesIO()
    Image.new("RGB", (400, 250), "white").save(buffer, format="PNG")
    return buffer.getvalue()


class _FakeEngine(ocr.OcrEngine):
    name = "fake"

    def read_text(self, image):
        return "TEXTO DE PRUEBA"


@tagged("post_install", "-at_install")
class TestOcrService(TransactionCase):

    def setUp(self):
        super().setUp()
        self.service = self.env["pdi.ocr.service"]

    def test_read_text_uses_the_configured_engine(self):
        with patch.object(type(self.service), "_get_engine", return_value=_FakeEngine()):
            self.assertEqual(self.service.read_text(_png_bytes()), "TEXTO DE PRUEBA")

    def test_invalid_image_raises_user_error(self):
        with patch.object(type(self.service), "_get_engine", return_value=_FakeEngine()):
            with self.assertRaises(UserError):
                self.service.read_text(b"no es una imagen")

    def test_ocr_error_is_shown_as_user_error(self):
        class _Broken(_FakeEngine):
            def read_text(self, image):
                raise ocr.OcrError("No se encontró Tesseract.")

        with patch.object(type(self.service), "_get_engine", return_value=_Broken()):
            with self.assertRaisesRegex(UserError, "No se encontró Tesseract"):
                self.service.read_text(_png_bytes())

    def test_engine_reads_settings(self):
        params = self.env["ir.config_parameter"].sudo()
        params.set_param("pdi_identity.tesseract_cmd", "/opt/bin/tesseract")
        params.set_param("pdi_identity.ocr_lang", "spa+eng")
        engine = self.service._get_engine()
        self.assertEqual(engine.cmd, "/opt/bin/tesseract")
        self.assertEqual(engine.lang, "spa+eng")

    def test_engine_defaults_to_spanish(self):
        params = self.env["ir.config_parameter"].sudo()
        params.set_param("pdi_identity.tesseract_cmd", "")
        params.set_param("pdi_identity.ocr_lang", "")
        engine = self.service._get_engine()
        self.assertIsNone(engine.cmd)
        self.assertEqual(engine.lang, "spa")
