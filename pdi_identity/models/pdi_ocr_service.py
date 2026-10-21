# Part of odoo_pdi. See LICENSE file for full copyright and licensing details.
from odoo import api, models
from odoo.exceptions import UserError

from ..tools import image_preprocess, ocr


class PdiOcrService(models.AbstractModel):
    """Punto único para convertir la imagen de un documento en texto."""

    _name = "pdi.ocr.service"
    _description = "Servicio de OCR para identificaciones"

    @api.model
    def _get_engine(self):
        """Motor de OCR según los ajustes. Se puede sobrescribir para otro motor."""
        params = self.env["ir.config_parameter"].sudo()
        return ocr.TesseractEngine(
            cmd=params.get_param("pdi_identity.tesseract_cmd") or None,
            lang=params.get_param("pdi_identity.ocr_lang") or ocr.DEFAULT_LANG,
        )

    @api.model
    def read_text(self, image_data):
        """Preprocesa la imagen y devuelve el texto que lee el OCR.

        :param bytes image_data: contenido del archivo de imagen (sin base64).
        :raises UserError: si la imagen no es válida o el OCR no puede correr.
        """
        try:
            image = image_preprocess.preprocess(image_data)
            return self._get_engine().read_text(image)
        except (image_preprocess.ImageError, ocr.OcrError) as exc:
            raise UserError(str(exc)) from exc
