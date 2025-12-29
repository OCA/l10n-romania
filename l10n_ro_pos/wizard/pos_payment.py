# ©  2015-2018 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details

from odoo import api, models


class PosMakePayment(models.TransientModel):
    _inherit = "pos.make.payment"

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get("active_id")
        if active_id:
            session = self.env["pos.order"].browse(active_id).session_id
            for journal in session.config_id.journal_ids:
                if journal.type == "cash":
                    res["journal_id"] = journal.id

        return res
