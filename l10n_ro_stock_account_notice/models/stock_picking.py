# Copyright (C) 2022 cbssolutions.ro
# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    # Prin acest camp se indica daca un produs care e stocabil trece prin
    # contul 408 / 418 la achizitie sau vanzare
    # receptie/ livrare in baza de aviz
    l10n_ro_notice = fields.Boolean(
        "Is a notice",
        states={"done": [("readonly", True)], "cancel": [("readonly", True)]},
        default=False,
        help="With this field the reception/delivery is set as a notice. "
        "With this field set, at reception you can set the value of received products."
        "At post will create a account_move with accounts 408/418."
        "In Romanian language notice = marfa este trimisa/receptionata cu aviz (factura e ulterioara)",
    )
    # maybe also in l10n_ro_stock_account to know when is the innvoice/bill?
    l10n_ro_accounting_date = fields.Datetime(
        "Accounting Date",
        copy=False,
        help="If this field is set, the svl and accounting entiries will "
        "have this date, If not will have the today date.",
        tracking=True,
    )

    # we created 2 fields to be more clear in fields and at selection without so much code
    l10n_ro_notice_invoice_id = fields.Many2one(
        "account.move",
        readonly=1,
        help="This notice picking was invoiced in this invoice",
    )
    l10n_ro_notice_bill_id = fields.Many2one(
        "account.move", readonly=1, help="This notice picking was billed in this bill"
    )

    @api.constrains("picking_type_id", "l10n_ro_notice", "l10n_ro_accounting_date")
    def _check_picking_type_code_notice(self):
        for rec in self:
            if rec.l10n_ro_notice and rec.picking_type_id.code not in [
                "incoming",
                "outgoing",
            ]:
                raise ValidationError(
                    _(
                        f'For picking=({rec.id},{rec.name}) you have l10n_ro_notice but picking_type_code={rec.picking_type_code} that is not in ["incoming", "outgoing"]'
                    )
                )
            if (
                rec.l10n_ro_accounting_date
                and rec.l10n_ro_accounting_date
                > fields.datetime.now() + timedelta(days=2)
            ):
                raise ValidationError(
                    _(
                        f"For picking=({rec.id},{rec.name}) you can not set a l10n_ro_accounting_date in future!"
                    )
                )
