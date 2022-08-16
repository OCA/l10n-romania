# 2022 Nexterp Romania SRL
# ©  2008-2020 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details

from odoo import _, fields, models
from odoo.exceptions import ValidationError


class AccountInvoice(models.Model):
    _inherit = "account.move"

    l10n_ro_dvi_ids = fields.One2many(
        "stock.landed.cost",
        "vendor_bill_id",
        compute="_compute_l10n_ro_dvi_ids",
        string="DVI's",
        help="dvi are implemented as landed costs",
    )

    def _compute_l10n_ro_dvi_ids(self):
        for rec in self:
            l10n_ro_dvi_ids = self.env["stock.landed.cost"].search(
                [("vendor_bill_id", "in", rec.ids), ("l10n_ro_landed_type", "=", "dvi")]
            )
            rec.l10n_ro_dvi_ids = [(6, 0, l10n_ro_dvi_ids.ids)]

    #
    def button_create_dvi(self):
        self.ensure_one()
        if not self.company_id.l10n_ro_accounting:
            raise ValidationError(_("This button is only for Romanian accounting"))

        if self.company_id == self.partner_id.company_id:
            raise ValidationError(
                _(
                    "You can not create a DVI if the invoicing partner has same"
                    " country as your company."
                )
            )
        if not self.is_purchase_document():
            raise ValidationError(
                _(
                    "You can not create a dvi for a invoice that is not a puchase invoice"
                )
            )

        if not self._context.get(
            "is_installed_l10n_ro_stock_landed_cost_dvi_revert"
        ) and self.l10n_ro_dvi_ids.filtered(lambda r: r.l10n_ro_landed_type == "dvi"):
            raise ValidationError(
                _(
                    "You have already a DVI for this invoice. "
                    # "First revert that one than create another one."
                )
            )

        # generare dvi
        action = self.env.ref("l10n_ro_dvi.action_account_invoice_dvi")
        action = action.sudo().read()[0]
        return action

    def action_view_dvis(self):
        if not self.l10n_ro_dvi_ids:
            raise ValidationError(_("You Do not have created DVI's for this invoice"))
        action = self.env.ref("stock_landed_costs.action_stock_landed_cost")
        action = action.sudo().read()[0]
        #        action["res_id"] = self.dvi_ids
        action["domain"] = f"[('id','in',{self.l10n_ro_dvi_ids.ids})]"
        return action
