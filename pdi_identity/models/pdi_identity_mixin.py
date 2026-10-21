# Part of odoo_pdi. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class PdiIdentityMixin(models.AbstractModel):
    """Campos y acciones comunes de los modelos que se pueden llenar con una
    identificación (``res.partner`` y ``hr.employee``)."""

    _name = "pdi.identity.mixin"
    _description = "Campos y acciones comunes para escanear identificaciones"

    pdi_curp = fields.Char(
        string="CURP", copy=False, groups="pdi_identity.group_pdi_identity_user"
    )
    pdi_elector_key = fields.Char(
        string="Clave de elector", copy=False, groups="pdi_identity.group_pdi_identity_user"
    )
    pdi_ine_validity_year = fields.Integer(
        string="Vigencia de la INE", copy=False, groups="pdi_identity.group_pdi_identity_user"
    )

    def _pdi_identity_prepare_vals(self, data):
        """Valores a escribir en el registro a partir de los datos revisados.

        Cada modelo extiende este método con sus propios campos.

        :param dict data: datos del asistente (ver ``pdi.identity.scan._get_data``).
        :rtype: dict
        """
        return {
            "pdi_curp": data.get("curp"),
            "pdi_elector_key": data.get("elector_key"),
            "pdi_ine_validity_year": data.get("validity_year"),
        }

    def action_pdi_scan_identity(self):
        """Abre el asistente para completar este registro con una INE."""
        self.ensure_one()
        return self.env["pdi.identity.scan"]._get_action(self._name, self.id)

    def action_pdi_create_from_identity(self):
        """Abre el asistente para crear un registro nuevo desde una INE.

        Se usa desde el botón de la vista de lista: no necesita registros
        seleccionados. Los valores por defecto de la lista (por ejemplo, el
        rol de proveedor) se conservan al crear el registro.
        """
        defaults = {
            key: value for key, value in self.env.context.items()
            if key.startswith("default_")
        }
        return self.env["pdi.identity.scan"]._get_action(self._name, extra_context=defaults)
