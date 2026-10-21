# Part of odoo_pdi. See LICENSE file for full copyright and licensing details.
import io

from PIL import Image

from odoo.tests.common import BaseCase, tagged

from ..tools import image_preprocess


def _png(image):
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


@tagged("post_install", "-at_install")
class TestImagePreprocess(BaseCase):

    def test_low_contrast_is_stretched(self):
        # Imagen "lavada": solo usa los grises 100-140.
        image = Image.new("L", (400, 250))
        image.putdata([100 + (i % 41) for i in range(400 * 250)])
        result = image_preprocess.preprocess(_png(image))
        low, high = result.getextrema()
        self.assertLessEqual(low, 5)
        self.assertGreaterEqual(high, 250)
        self.assertEqual(result.mode, "L")

    def test_small_image_is_upscaled_to_min_width(self):
        result = image_preprocess.preprocess(_png(Image.new("RGB", (400, 250), "white")))
        self.assertEqual(result.width, image_preprocess.MIN_WIDTH)
        self.assertEqual(result.height, round(250 * image_preprocess.MIN_WIDTH / 400))

    def test_huge_image_is_downscaled(self):
        result = image_preprocess.preprocess(
            _png(Image.new("L", (5000, 100), 128)), min_width=100
        )
        self.assertEqual(max(result.size), image_preprocess.MAX_SIDE)

    def test_exif_orientation_is_applied(self):
        image = Image.new("RGB", (300, 100), "white")
        exif = Image.Exif()
        exif[0x0112] = 6  # girar 90° para mostrarla derecha
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", exif=exif.tobytes())
        result = image_preprocess.preprocess(buffer.getvalue(), min_width=100)
        self.assertEqual(result.size, (100, 300))

    def test_binarize_returns_only_black_and_white(self):
        image = Image.new("L", (400, 250))
        image.putdata([40 if (i // 400) < 125 else 220 for i in range(400 * 250)])
        result = image_preprocess.preprocess(_png(image), binarize=True)
        self.assertEqual({value for _count, value in result.getcolors()}, {0, 255})

    def test_otsu_threshold_separates_two_tones(self):
        image = Image.new("L", (100, 100))
        image.putdata([30 if i % 2 else 200 for i in range(100 * 100)])
        threshold = image_preprocess.otsu_threshold(image)
        self.assertTrue(30 <= threshold < 200)

    def test_invalid_data_raises_image_error(self):
        with self.assertRaises(image_preprocess.ImageError):
            image_preprocess.preprocess(b"esto no es una imagen")
        with self.assertRaises(image_preprocess.ImageError):
            image_preprocess.preprocess(b"")
