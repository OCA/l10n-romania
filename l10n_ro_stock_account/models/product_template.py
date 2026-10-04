# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import fields, models

from odoo.addons.account.models.product import ACCOUNT_DOMAIN

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = ("product.template", "l10n.ro.mixin")

    l10n_ro_property_stock_valuation_account_id = fields.Many2one(
        "account.account",
        string="Stock Valuation Account",
        ondelete="restrict",
        company_dependent=True,
        domain=ACCOUNT_DOMAIN,
        help="In Romania accounting is only one account for valuation/input/"
        "output. If this value is set, we will use it, otherwise will "
        "use the category value. ",
    )

    def _l10n_ro_apply_location_accounts(self, accounts, stock_move):
        """Take the accounts off the location the goods move through, which is
        the source when it is internal and the destination otherwise."""
        location = (
            stock_move.location_id
            if stock_move.location_id.usage == "internal"
            else stock_move.location_dest_id
        )
        inc_acc = location.l10n_ro_property_account_income_location_id
        exp_acc = location.l10n_ro_property_account_expense_location_id
        stock_acc = location.l10n_ro_property_stock_valuation_account_id

        if inc_acc:
            accounts["income"] = inc_acc
        # `exp_acc` comes from the source location for an internal transfer
        # (the source is internal), and would send the incoming leg to an
        # expense account instead of the destination warehouse.
        if exp_acc and stock_move.l10n_ro_move_type != "internal_transfer":
            accounts["expense"] = exp_acc
        if stock_acc:
            accounts["stock_valuation"] = stock_acc

    def _l10n_ro_add_company_accounts(self, accounts, company):
        """The Romanian-specific accounts, as the company configures them."""
        for key, field in [
            ("l10n_ro_picking_payable", "picking_payable"),
            ("l10n_ro_picking_receivable", "picking_receivable"),
            ("l10n_ro_usage_giving", "usage_giving"),
            ("l10n_ro_transfer", "transfer"),
        ]:
            account = company[f"l10n_ro_property_stock_{field}_account_id"]
            if account:
                accounts[key] = account

    def _get_product_accounts(self):
        accounts = super()._get_product_accounts()
        company = self.company_id or self.env.company
        if not company.l10n_ro_accounting:
            return accounts

        stock_move = self.env.context.get("l10n_ro_stock_move")
        if not stock_move or not stock_move.is_l10n_ro_record:
            return accounts
        src_location = stock_move.location_id
        dest_location = stock_move.location_dest_id
        if stock_move.l10n_ro_move_type == "internal_transfer":
            # The incoming leg of a transfer takes the goods into the
            # destination warehouse, so the `expense` key carries its
            # valuation account, not an expense account. The destination's own
            # account only counts when the category asks for the location
            # accounts; otherwise both legs resolve to the product's valuation
            # account and the entry is dropped as a whole further down.
            dest_valuation = self.env["account.account"]
            if self.categ_id.l10n_ro_stock_account_change:
                dest_valuation = (
                    dest_location.l10n_ro_property_stock_valuation_account_id
                )
            accounts["expense"] = dest_valuation or accounts["stock_valuation"]
        if self.categ_id.l10n_ro_stock_account_change:
            self._l10n_ro_apply_location_accounts(accounts, stock_move)
        self._l10n_ro_add_company_accounts(accounts, company)
        if (
            stock_move.l10n_ro_move_type
            in [
                "consumption",
                "consumption_return",
                "usage_giving",
                "usage_giving_return",
            ]
            and accounts["expense"].l10n_ro_stock_consume_account_id
        ):
            accounts["expense"] = accounts["expense"].l10n_ro_stock_consume_account_id
        if accounts["stock_valuation"].l10n_ro_reception_in_progress_account_id:
            accounts["l10n_ro_reception_in_progress"] = accounts[
                "stock_valuation"
            ].l10n_ro_reception_in_progress_account_id

        warehouse = src_location.warehouse_id or dest_location.warehouse_id
        if warehouse and warehouse.l10n_ro_fiscal_position_id:
            for key in accounts.keys() - {"stock_journal"}:
                if accounts.get(key):
                    accounts[key] = warehouse.l10n_ro_fiscal_position_id.map_account(
                        accounts[key]
                    )
        return accounts
