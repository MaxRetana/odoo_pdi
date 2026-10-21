# Part of odoo_pdi. See LICENSE file for full copyright and licensing details.
from odoo import models


class HrEmployee(models.Model):
    _name = "hr.employee"
    _inherit = ["hr.employee", "pdi.identity.mixin"]

    def _pdi_identity_prepare_vals(self, data):
        vals = super()._pdi_identity_prepare_vals(data)
        birth_state = self.env["res.country.state"].browse(data.get("birth_state_id"))
        vals.update({
            "name": data.get("full_name"),
            "birthday": data.get("birth_date"),
            "sex": data.get("gender"),
            # La CURP es el número de identificación nacional de México.
            "identification_id": data.get("curp"),
            # La INE solo la tienen los ciudadanos mexicanos.
            "country_id": data.get("country_id"),
            "place_of_birth": birth_state.name,
            "country_of_birth": birth_state.country_id.id,
            # El domicilio de la INE es el domicilio privado del empleado.
            "private_street": data.get("street"),
            "private_street2": data.get("street2"),
            "private_zip": data.get("zip"),
            "private_city": data.get("city"),
            "private_state_id": data.get("state_id"),
            "private_country_id": data.get("country_id"),
        })
        return vals
