# Copyright (C) 2022 cbssolutions.ro
# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2022 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models


class StockValuationLayer(models.Model):
    _inherit = "stock.valuation.layer"

    l10n_ro_valued_type = fields.Char()  # just a name we can live also without
    l10n_ro_bill_accounting_date = fields.Date(
        help="This is the date from billing accounting date. The bill that generate this svl",
    )
    # fields to work the set to draft and post again to change the values/ date
    l10n_ro_draft_svl_id = fields.Many2one(
        "stock.valuation.layer",
        help="was created from a setting to draft. is the reverse of this svl",
    )
    l10n_ro_draft_svl_ids = fields.One2many(
        "stock.valuation.layer",
        "l10n_ro_draft_svl_id",
        help="it's value was nulled (at setting to draft the account_move) by this entry",
    )
    # just for valued reports per location
    l10n_ro_location_dest_id = fields.Many2one(
        "stock.location",
        store=1,
        related="stock_move_id.location_dest_id",
        help="Destination Location value taken from move to be able to aproximate the value of stock in a location",
    )
    # we must create this field for draft notice picking svl
    # can not use remaining value because is modiffing all the time with landed_cost, with out moves ..
    l10n_ro_modified_value = fields.Float(
        help="This value is used to keep the modified value after reposing a journal entry. Used in stock_account_notice to make difference from this actual value (value that is in account 409/419)"
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
