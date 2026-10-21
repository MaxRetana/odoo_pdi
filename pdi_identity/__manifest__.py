# Part of odoo_pdi. See LICENSE file for full copyright and licensing details.
{
    "name": "Escaneo de identificaciones (PDI)",
    "summary": "Crea contactos y empleados a partir de la imagen de una INE",
    "description": """
Procesamiento digital de imágenes (PDI) y OCR para leer una identificación
oficial y llenar el registro sin teclear.
""",
    "version": "19.0.1.0.0",
    "category": "Productivity",
    "author": "MaxRetana",
    "website": "https://github.com/MaxRetana/odoo_pdi",
    "license": "LGPL-3",
    "depends": ["hr"],
    "external_dependencies": {"python": ["Pillow", "pytesseract"]},
    "data": [
        "security/pdi_identity_security.xml",
        "security/ir.model.access.csv",
        "views/pdi_identity_scan_views.xml",
        "views/res_partner_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": False,
}
