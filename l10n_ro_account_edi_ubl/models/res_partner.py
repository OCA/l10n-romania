# Copyright (C) 2022 Dorin Hongu <dhongu(@)gmail(.)com
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_ro_is_government_institution = fields.Boolean(
        "Romania - Is government institution",
        help="Check this if the partner is a government institution."
        "Will be used to calculate the sending of the invoice to "
        "the e-invoice system.",
    )

    @api.onchange("l10n_ro_is_government_institution", "l10n_ro_e_invoice")
    def _onchange_einvoice_government(self):
        if self.l10n_ro_is_government_institution:
            self.l10n_ro_e_invoice = True
