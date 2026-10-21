# Part of odoo_pdi. See LICENSE file for full copyright and licensing details.
from odoo import models


class ResPartner(models.Model):
    _name = "res.partner"
    _inherit = ["res.partner", "pdi.identity.mixin"]

    def _pdi_identity_prepare_vals(self, data):
        vals = super()._pdi_identity_prepare_vals(data)
        vals.update({
            "name": data.get("full_name"),
            "company_type": "person",
            "street": data.get("street"),
            "street2": data.get("street2"),
            "zip": data.get("zip"),
            "city": data.get("city"),
            "state_id": data.get("state_id"),
            "country_id": data.get("country_id"),
        })
        return vals
