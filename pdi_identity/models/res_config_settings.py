# Part of odoo_pdi. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pdi_tesseract_cmd = fields.Char(
        string="Ruta de Tesseract",
        config_parameter="pdi_identity.tesseract_cmd",
        help="Ruta completa del binario de Tesseract. Déjalo vacío si está en el PATH del servidor.",
    )
    pdi_ocr_lang = fields.Char(
        string="Idioma del OCR",
        config_parameter="pdi_identity.ocr_lang",
        default="spa",
        help="Código de idioma de Tesseract. Ejemplos: spa, spa+eng.",
    )
    pdi_keep_images = fields.Boolean(
        string="Conservar las imágenes",
        config_parameter="pdi_identity.keep_images",
        help="Adjunta las imágenes de la identificación al registro creado. "
             "Por defecto no se conservan: contienen datos personales sensibles.",
    )
