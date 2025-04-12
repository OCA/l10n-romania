# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = ["product.template", "l10n.ro.mixin"]

    l10n_ro_property_stock_valuation_account_id = fields.Many2one(
        "account.account",
        string="Stock Valuation Account",
        company_dependent=True,
        domain="[('deprecated', '=', False)]",
        check_company=True,
        help="In Romania accounting is only one account for valuation/input/"
        "output. If this value is set, we will use it, otherwise will "
        "use the category value. ",
    )

    def get_product_accounts(self, fiscal_pos=None):
        fiscal_pos = fiscal_pos or self.env.context.get("fiscal_pos")
        return super().get_product_accounts(fiscal_pos)

    def _get_product_accounts(self):
        accounts = super()._get_product_accounts()

        company = (
            self.env["res.company"].browse(self._context.get("force_company"))
            or self.env.company
        )
        if not company.l10n_ro_accounting:
            return accounts

        if not self.is_storable:
            accounts["stock_input"] = accounts["expense"]
            return accounts

        stock_valuation_account = (
            self.l10n_ro_property_stock_valuation_account_id
            or self.categ_id.property_stock_valuation_account_id
        )
        stock_usage_giving_account = (
            company.l10n_ro_property_stock_usage_giving_account_id
        )
        stock_transfer_account = company.l10n_ro_property_stock_transfer_account_id

        if stock_valuation_account:
            accounts.update(
                {
                    "stock_input": stock_valuation_account,
                    "stock_output": stock_valuation_account,
                    "stock_valuation": stock_valuation_account,
                }
            )

        valued_type = self.env.context.get("valued_type", "indefinite")
        _logger.debug(valued_type)

        # in Romania iesirea din stoc de face de regula pe contul de cheltuiala
        if valued_type in [
            "delivery",
            "consumption",
            "production_return",
            "minus_inventory",
            "usage_giving",
        ]:
            accounts["stock_output"] = accounts["expense"]

        # intrare in stoc
        elif valued_type in [
            "production",
            "consumption_return",
            "delivery_return",
            "usage_giving_return",
            "plus_inventory",
        ]:
            accounts["stock_input"] = accounts["stock_output"] = accounts["expense"]
        elif valued_type == "dropshipped":
            accounts["stock_output"] = accounts["expense"]

        # suplimentar la darea in consum mai face o nota contabila
        elif valued_type == "usage_giving_secondary":
            accounts["stock_output"] = stock_usage_giving_account
            accounts["stock_input"] = stock_usage_giving_account
            accounts["stock_valuation"] = stock_usage_giving_account

        elif valued_type == "internal_transit_out":
            accounts["stock_input"] = stock_transfer_account

        elif valued_type == "internal_transit_in":
            accounts["stock_output"] = stock_transfer_account

        return accounts
