# Copyright (C) 2020 Terrabit
# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from odoo import _, fields, models
from odoo.exceptions import ValidationError


class AccountInvoice(models.Model):
    _inherit = "account.move"

    l10n_ro_dvi_ids = fields.Many2many(
        "stock.landed.cost",
        compute="_compute_l10n_ro_dvi_ids",
        string="Romania - DVI's",
        help="DVI's linked to this invoice",
    )

    def _compute_l10n_ro_dvi_ids(self):
        for invoice in self:
            invoice.l10n_ro_dvi_ids = [
                (
                    6,
                    0,
                    self.env["l10n.ro.account.dvi"]
                    .search([("invoice_ids", "=", invoice.id)])
                    .ids,
                )
            ]

    def action_view_dvis(self):
        self.ensure_one()
        if not self.l10n_ro_dvi_ids:
            raise ValidationError(_("You do not have created DVI's for this invoice"))
        action = self.env.ref("l10n_ro_dvi.action_account_dvi")
        action = action.sudo().read()[0]
        action["domain"] = [("id", "in", self.l10n_ro_dvi_ids.ids)]
        return action
