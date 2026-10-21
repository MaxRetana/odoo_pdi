# Part of odoo_pdi. See LICENSE file for full copyright and licensing details.
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

from odoo.tests.common import BaseCase, tagged

from ..tools import ocr


class _NotFound(Exception):
    pass


class _TesseractError(Exception):
    pass


def _fake_pytesseract(confidence_of=lambda image: 90, text="HOLA MUNDO", error=None):
    """Sustituto de ``pytesseract`` que registra con qué imagen se le llamó."""
    fake = SimpleNamespace(
        TesseractNotFoundError=_NotFound,
        TesseractError=_TesseractError,
        Output=SimpleNamespace(DICT="dict"),
        pytesseract=SimpleNamespace(tesseract_cmd="tesseract"),
        read_images=[],
    )

    def image_to_data(image, **kwargs):
        if error:
            raise error
        return {"text": ["hola", "mundo", " "], "conf": [confidence_of(image)] * 2 + [-1]}

    def image_to_string(image, **kwargs):
        if error:
            raise error
        fake.read_images.append(image)
        fake.kwargs = kwargs
        return text

    fake.image_to_data = image_to_data
    fake.image_to_string = image_to_string
    return fake


@tagged("post_install", "-at_install")
class TestTesseractEngine(BaseCase):

    def _engine(self, fake, **kwargs):
        engine = ocr.TesseractEngine(**kwargs)
        patcher = patch.object(ocr, "_import_pytesseract", return_value=fake)
        patcher.start()
        self.addCleanup(patcher.stop)
        return engine

    def test_read_text_returns_text(self):
        fake = _fake_pytesseract()
        engine = self._engine(fake, auto_rotate=False)
        self.assertEqual(engine.read_text(Image.new("L", (200, 100))), "HOLA MUNDO")
        self.assertEqual(fake.kwargs["lang"], "spa")

    def test_cmd_and_lang_are_applied(self):
        fake = _fake_pytesseract()
        engine = self._engine(fake, cmd="/opt/bin/tesseract", lang="spa+eng", auto_rotate=False)
        engine.read_text(Image.new("L", (200, 100)))
        self.assertEqual(fake.pytesseract.tesseract_cmd, "/opt/bin/tesseract")
        self.assertEqual(fake.kwargs["lang"], "spa+eng")

    def test_auto_rotate_keeps_the_orientation_read_with_more_confidence(self):
        # La foto llega de cabeza: el pixel (0, 0) es negro y el opuesto, blanco.
        image = Image.new("L", (200, 100), 128)
        image.putpixel((0, 0), 0)
        image.putpixel((199, 99), 255)
        # Gira 180° y entonces el pixel (0, 0) es blanco: ahí "lee" mejor.
        fake = _fake_pytesseract(confidence_of=lambda img: 95 if img.getpixel((0, 0)) == 255 else 10)
        engine = self._engine(fake)
        engine.read_text(image)
        self.assertEqual(fake.read_images[0].getpixel((0, 0)), 255)

    def test_auto_rotate_tries_quarter_turns_for_portrait_images(self):
        seen = []
        fake = _fake_pytesseract(confidence_of=lambda img: seen.append(img.size) or 50)
        engine = self._engine(fake)
        engine.read_text(Image.new("L", (100, 200)))
        # Vertical: se prueban giros de 90° y 270°, que producen una imagen horizontal.
        self.assertTrue(all(width > height for width, height in seen))

    def test_missing_tesseract_gives_a_friendly_error(self):
        fake = _fake_pytesseract(error=_NotFound())
        engine = self._engine(fake, auto_rotate=False)
        with self.assertRaisesRegex(ocr.OcrError, "No se encontró Tesseract"):
            engine.read_text(Image.new("L", (200, 100)))

    def test_missing_language_gives_a_friendly_error(self):
        fake = _fake_pytesseract(error=_TesseractError("Failed loading language"))
        engine = self._engine(fake, lang="xyz", auto_rotate=False)
        with self.assertRaisesRegex(ocr.OcrError, "xyz"):
            engine.read_text(Image.new("L", (200, 100)))
