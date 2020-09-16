# ©  2008-2020 Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    intrastat_transaction_id = fields.Many2one(
        "l10n_ro_intrastat.transaction",
        "Intrastat Transaction Type",
        help="Intrastat nature of transaction",
    )
    transport_mode_id = fields.Many2one(
        "l10n_ro_intrastat.transport_mode", "Intrastat Transport Mode"
    )
    intrastat_country_id = fields.Many2one(
        "res.country",
        string="Intrastat Country",
        help="Intrastat country, delivery for sales, origin for purchases",
        domain=[("intrastat", "=", True)],
    )

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        res = super(AccountMove, self)._onchange_partner_id()
        if self.partner_id.country_id.intrastat:
            self.intrastat_country_id = self._get_invoice_intrastat_country_id()
        else:
            self.intrastat_country_id = False
        return res
