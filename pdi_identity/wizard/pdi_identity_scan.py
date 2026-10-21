# Part of odoo_pdi. See LICENSE file for full copyright and licensing details.
import base64

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..tools import ine_parser, mx_states


class PdiIdentityScan(models.TransientModel):
    """Sube la imagen de una identificación, la lee con OCR y deja revisar los
    datos antes de crear o completar un registro."""

    _name = "pdi.identity.scan"
    _description = "Escaneo de identificación"

    step = fields.Selection(
        [("draft", "Cargar imágenes"), ("review", "Revisar datos")],
        default="draft", required=True,
    )
    target_model = fields.Selection(
        [("res.partner", "Contacto"), ("hr.employee", "Empleado")],
        string="Modelo destino", required=True,
    )
    target_res_id = fields.Integer(
        string="Registro destino",
        help="Si se indica, se completa ese registro; si no, se crea uno nuevo.",
    )
    document_type = fields.Selection(
        [("ine", "INE")], string="Documento", default="ine", required=True
    )
    front_image = fields.Binary(string="Frente", attachment=True)
    back_image = fields.Binary(string="Reverso (opcional)", attachment=True)

    # Datos extraídos: el usuario los revisa y corrige antes de guardar.
    first_name = fields.Char(string="Nombre(s)")
    paternal_surname = fields.Char(string="Apellido paterno")
    maternal_surname = fields.Char(string="Apellido materno")
    curp = fields.Char(string="CURP")
    elector_key = fields.Char(string="Clave de elector")
    birth_date = fields.Date(string="Fecha de nacimiento")
    gender = fields.Selection(
        [("male", "Hombre"), ("female", "Mujer")], string="Sexo"
    )
    birth_state_id = fields.Many2one(
        "res.country.state", string="Estado de nacimiento",
        domain="[('country_id.code', '=', 'MX')]",
    )
    street = fields.Char(string="Calle y número")
    street2 = fields.Char(string="Colonia")
    zip = fields.Char(string="C.P.")
    city = fields.Char(string="Ciudad o municipio")
    country_id = fields.Many2one("res.country", string="País")
    state_id = fields.Many2one(
        "res.country.state", string="Estado",
        domain="[('country_id', '=?', country_id)]",
    )
    validity_year = fields.Integer(string="Vigencia (año)")
    warnings = fields.Text(string="Advertencias", readonly=True)

    # ------------------------------------------------------------------
    # Apertura
    # ------------------------------------------------------------------

    @api.model
    def _get_action(self, target_model, target_res_id=False, extra_context=None):
        """Acción que abre el asistente para ``target_model``.

        :param dict extra_context: contexto que se conserva al crear el
            registro (por ejemplo, ``default_supplier_rank``).
        """
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "pdi_identity.pdi_identity_scan_action"
        )
        action["context"] = {
            **(extra_context or {}),
            "default_target_model": target_model,
            "default_target_res_id": target_res_id or 0,
        }
        return action

    def _reopen(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------

    def action_scan(self):
        """Lee las imágenes y pasa al paso de revisión."""
        self.ensure_one()
        if not self.front_image:
            raise UserError(_("Carga al menos la imagen del frente de la INE."))
        service = self.env["pdi.ocr.service"]
        front_text = service.read_text(base64.b64decode(self.front_image))
        back_text = ""
        if self.back_image:
            back_text = service.read_text(base64.b64decode(self.back_image))
        data = ine_parser.parse_ine(front_text, back_text)
        if not (data.curp or data.full_name):
            raise UserError(_(
                "No se pudieron leer datos de la INE. Verifica que la imagen "
                "sea nítida, esté completa, bien iluminada y sin reflejos."
            ))
        self._fill_from_data(data)
        self.step = "review"
        return self._reopen()

    @staticmethod
    def _title(text):
        return text.title() if text else False

    def _find_state(self, country, code):
        if not (country and code):
            return self.env["res.country.state"]
        return self.env["res.country.state"].search(
            [("country_id", "=", country.id), ("code", "=", code)], limit=1
        )

    def _fill_from_data(self, data):
        """Copia el resultado del parser a los campos editables."""
        self.ensure_one()
        mexico = self.env.ref("base.mx", raise_if_not_found=False)
        state = self._find_state(mexico, mx_states.odoo_state_code(data.state))
        birth_state = self._find_state(
            mexico, mx_states.odoo_state_code_from_curp(data.birth_state_code)
        )
        self.write({
            "first_name": self._title(data.first_name),
            "paternal_surname": self._title(data.paternal_surname),
            "maternal_surname": self._title(data.maternal_surname),
            "curp": data.curp,
            "elector_key": data.elector_key,
            "birth_date": data.birth_date,
            "gender": data.gender,
            "birth_state_id": birth_state.id,
            "street": self._title(data.street),
            "street2": self._title(data.street2),
            "zip": data.zip,
            "city": self._title(data.city),
            "country_id": mexico.id if mexico else False,
            "state_id": state.id,
            "validity_year": data.validity_year or 0,
            "warnings": "\n".join(data.warnings) or False,
        })

    def action_back(self):
        """Regresa al paso de carga de imágenes."""
        self.ensure_one()
        self.step = "draft"
        return self._reopen()

    # ------------------------------------------------------------------
    # Aplicación
    # ------------------------------------------------------------------

    def _get_data(self):
        """Datos revisados por el usuario, en el formato que reciben los
        modelos destino en ``_pdi_identity_prepare_vals``."""
        self.ensure_one()
        names = (self.first_name, self.paternal_surname, self.maternal_surname)
        return {
            "first_name": self.first_name,
            "paternal_surname": self.paternal_surname,
            "maternal_surname": self.maternal_surname,
            "full_name": " ".join(name.strip() for name in names if name and name.strip()),
            "curp": (self.curp or "").strip().upper() or False,
            "elector_key": (self.elector_key or "").strip().upper() or False,
            "birth_date": self.birth_date,
            "gender": self.gender,
            "birth_state_id": self.birth_state_id.id,
            "street": self.street,
            "street2": self.street2,
            "zip": self.zip,
            "city": self.city,
            "country_id": self.country_id.id,
            "state_id": self.state_id.id,
            "validity_year": self.validity_year or False,
        }

    def _attach_images(self, record):
        """Adjunta las imágenes al registro (solo si el ajuste lo permite)."""
        for field_name, label in (("front_image", "INE (frente)"), ("back_image", "INE (reverso)")):
            if self[field_name]:
                self.env["ir.attachment"].create({
                    "name": label,
                    "datas": self[field_name],
                    "res_model": record._name,
                    "res_id": record.id,
                })

    def action_apply(self):
        """Crea o completa el registro con los datos revisados."""
        self.ensure_one()
        target = self.env[self.target_model]
        data = self._get_data()
        if not data["full_name"] and not data["curp"]:
            raise UserError(_("Captura al menos el nombre o la CURP."))
        # Solo se escriben valores con contenido: no se borra lo que ya tiene
        # el registro por un dato que el OCR no pudo leer.
        vals = {k: v for k, v in target._pdi_identity_prepare_vals(data).items() if v}
        if self.target_res_id:
            record = target.browse(self.target_res_id).exists()
            if not record:
                raise UserError(_("El registro que se iba a completar ya no existe."))
            record.write(vals)
        else:
            record = target.create(vals)
        keep_images = self.env["ir.config_parameter"].sudo().get_param("pdi_identity.keep_images")
        if keep_images:
            self._attach_images(record)
        # Las imágenes tienen datos personales: no se conservan en el asistente.
        self.write({"front_image": False, "back_image": False})
        return {
            "type": "ir.actions.act_window",
            "res_model": record._name,
            "res_id": record.id,
            "view_mode": "form",
            "target": "current",
        }
