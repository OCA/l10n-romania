# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2022 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models


class StockValuationLayer(models.Model):
    _inherit = "stock.valuation.layer"

    l10n_ro_valued_type = fields.Char()  # just a name we can live also without
    l10n_ro_bill_accounting_date = fields.Date(
        readonly=True,
        help="This is the date from billing accounting date. The bill that generate this svl",
    )
    l10n_ro_draft_history = fields.Text(
        help="Each time, the bill that generated this "
        "svl is put into draft we are recording values that we are changing with 0"
    )

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if self.env["res.company"]._check_is_l10n_ro_record(
                values.get("company_id")
            ):
                if (
                    "l10n_ro_valued_type" not in values
                    and "stock_valuation_layer_id" in values
                ):
                    svl = self.env["stock.valuation.layer"].browse(
                        values["stock_valuation_layer_id"]
                    )
                    if svl:
                        values["l10n_ro_valued_type"] = svl.l10n_ro_valued_type
        return super(StockValuationLayer, self).create(vals_list)
