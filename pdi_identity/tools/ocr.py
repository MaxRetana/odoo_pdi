# Part of odoo_pdi. See LICENSE file for full copyright and licensing details.
"""Motores de OCR.

La interfaz :class:`OcrEngine` permite cambiar de motor sin tocar el resto del
módulo. Hoy existe solo :class:`TesseractEngine`, que corre de forma local: los
datos de una identificación no salen del servidor.
"""
import logging

_logger = logging.getLogger(__name__)

DEFAULT_LANG = "spa"
# --psm 6: un solo bloque de texto uniforme, buen punto de partida para el
# frente de una INE. --oem 1: motor LSTM.
DEFAULT_CONFIG = "--oem 1 --psm 6"


class OcrError(Exception):
    """El OCR no pudo ejecutarse; el mensaje es apto para mostrarse al usuario."""


class OcrEngine:
    """Interfaz de un motor de OCR."""

    name = "base"

    def read_text(self, image):
        """Devuelve el texto de una imagen ``PIL.Image``."""
        raise NotImplementedError


def _import_pytesseract():
    try:
        import pytesseract
    except ImportError as exc:  # pragma: no cover - depende del entorno
        raise OcrError(
            "Falta el paquete de Python 'pytesseract'. "
            "Instálalo con: pip install pytesseract"
        ) from exc
    return pytesseract


class TesseractEngine(OcrEngine):
    """OCR con Tesseract a través de ``pytesseract``.

    :param str cmd: ruta del binario ``tesseract`` (``None`` = el del PATH).
    :param str lang: idioma(s) de Tesseract, por ejemplo ``spa`` o ``spa+eng``.
    :param str config: opciones extra de Tesseract.
    :param bool auto_rotate: probar la orientación de la foto y quedarse con la
        que Tesseract lea con más confianza.
    """

    name = "tesseract"

    def __init__(self, cmd=None, lang=DEFAULT_LANG, config=DEFAULT_CONFIG,
                 auto_rotate=True):
        self.cmd = cmd or None
        self.lang = lang or DEFAULT_LANG
        self.config = config
        self.auto_rotate = auto_rotate

    def _tesseract(self):
        pytesseract = _import_pytesseract()
        if self.cmd:
            pytesseract.pytesseract.tesseract_cmd = self.cmd
        return pytesseract

    def _mean_confidence(self, pytesseract, image):
        """Confianza media (0-100) de las palabras de 3+ caracteres."""
        data = pytesseract.image_to_data(
            image, lang=self.lang, config=self.config,
            output_type=pytesseract.Output.DICT,
        )
        scores = [
            float(conf)
            for text, conf in zip(data["text"], data["conf"])
            if len(text.strip()) >= 3 and float(conf) >= 0
        ]
        return sum(scores) / len(scores) if scores else 0.0

    def _best_orientation(self, pytesseract, image):
        """Elige entre la imagen y su giro de 180° (o 90°/270° si es vertical)."""
        angles = (0, 180) if image.width >= image.height else (90, 270)
        best_image, best_score = image, -1.0
        for angle in angles:
            candidate = image.rotate(angle, expand=True) if angle else image
            score = self._mean_confidence(pytesseract, candidate)
            if score > best_score:
                best_image, best_score = candidate, score
        return best_image

    def read_text(self, image):
        pytesseract = self._tesseract()
        try:
            if self.auto_rotate:
                image = self._best_orientation(pytesseract, image)
            return pytesseract.image_to_string(
                image, lang=self.lang, config=self.config
            )
        except pytesseract.TesseractNotFoundError as exc:
            raise OcrError(
                "No se encontró Tesseract. Instálalo en el servidor "
                "(por ejemplo: apt install tesseract-ocr tesseract-ocr-spa) o "
                "indica su ruta en Ajustes > Escaneo de identificaciones."
            ) from exc
        except pytesseract.TesseractError as exc:
            _logger.warning("Tesseract falló: %s", exc)
            raise OcrError(
                "Tesseract no pudo leer la imagen. Verifica que el idioma "
                "'%s' esté instalado." % self.lang
            ) from exc
