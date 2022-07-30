# Copyright (C) 2022 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class StockImmediateTransfer(models.TransientModel):
    _inherit = "stock.immediate.transfer"

    accounting_date = fields.Datetime(
        help="If this field is set, the svl and accounting entries will "
        "have this date, If not will have the today date as it should be",
        default=fields.Datetime.now(),
    )

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if res.get("pick_ids"):
            if (
                self.env["stock.picking"]
                .browse(res["pick_ids"][0][2][0])
                .accounting_date
            ):
                res["accounting_date"] = (
                    self.env["stock.picking"]
                    .browse(res["pick_ids"][0][2][0])
                    .accounting_date
                )
        return res

    def process(self):
        if self.accounting_date:

            self.env["stock.picking"].check_accounting_date(self.accounting_date)

            self.pick_ids.write(
                {
                    "accounting_date": self.accounting_date,
                    "date_done": self.accounting_date,
                }
            )
        return super().process()
