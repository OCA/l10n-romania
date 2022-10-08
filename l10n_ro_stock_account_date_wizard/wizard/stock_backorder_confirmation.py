# Copyright (C) 2022 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class StockBackorderConfirmation(models.TransientModel):
    _name = "stock.backorder.confirmation"
    _inherit = ["stock.backorder.confirmation", "l10n.ro.mixin"]

    l10n_ro_accounting_date = fields.Datetime(
        help="If this field is set, the svl and accounting entiries will "
        "have this date, If not will have the today date as it should be",
        default=fields.Datetime.now(),
    )

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if self.env["res.company"]._check_is_l10n_ro_record(self.env.company.id):
            res["is_l10n_ro_record"] = True
            if res.get("pick_ids"):
                if (
                    self.env["stock.picking"]
                    .browse(res["pick_ids"][0][2][0])
                    .l10n_ro_accounting_date
                ):
                    res["l10n_ro_accounting_date"] = (
                        self.env["stock.picking"]
                        .browse(res["pick_ids"][0][2][0])
                        .l10n_ro_accounting_date
                    )
        return res

    def process(self):
        if self.is_l10n_ro_record:
            if self.l10n_ro_accounting_date.date() > fields.date.today():
                raise ValidationError(
                    _(
                        "You can not have a Accounting date=%s for picking bigger than today!"
                        % self.l10n_ro_accounting_date.date()
                    )
                )
            self.pick_ids.write(
                {
                    "l10n_ro_accounting_date": self.l10n_ro_accounting_date,
                    "date_done": self.l10n_ro_accounting_date,
                }
            )
        return super().process()

    def process_cancel_backorder(self):
        if self.is_l10n_ro_record:
            pickings_to_validate = self.env.context.get("button_validate_picking_ids")
            if pickings_to_validate and self.l10n_ro_accounting_date:
                if self.l10n_ro_accounting_date.date() > fields.date.today():
                    raise ValidationError(
                        _(
                            "You can not have a Accounting date=%s "
                            "for picking bigger than today!"
                            % self.accounting_date.date()
                        )
                    )
                self.env["stock.picking"].browse(pickings_to_validate).write(
                    {
                        "l10n_ro_accounting_date": self.l10n_ro_accounting_date,
                        "date_done": self.l10n_ro_accounting_date,
                    }
                )
        return super().process_cancel_backorder()
