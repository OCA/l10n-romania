# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ProductCategory(models.Model):
    _inherit = "product.category"

    hide_stock_in_out_account = fields.Boolean(
        compute="_compute_hide_accounts",
        help="Only for Romania, to hide stock_input and stock_output "
        "accounts because they are the same as stock_valuation account",
    )
    stock_account_change = fields.Boolean(
        string="Allow stock account change from locations",
        help="Only for Romania, to change the accounts to the ones defined "
        "on stock locations",
    )

    @api.depends("name")
    def _compute_hide_accounts(self):
        for record in self:
            record.hide_stock_in_out_account = self.env.company.romanian_accounting

    @api.constrains(
        "property_stock_valuation_account_id",
        "property_stock_account_output_categ_id",
        "property_stock_account_input_categ_id",
    )
    def _check_valuation_accouts(self):
        """ Overwrite default constraint for Romania,
        stock_valuation, stock_output and stock_input
        are the same
        """
        if self.env.company.romanian_accounting:
            # is a romanian company:
            for record in self:
                stock_input = record.property_stock_account_input_categ_id
                stock_output = record.property_stock_account_output_categ_id
                stock_val = record.property_stock_valuation_account_id
                if not (stock_input == stock_output == stock_val):
                    raise UserError(
                        _(
                            "For Romanian Stock Accounting the stock_input, "
                            "stock_output and stock_valuation accounts must "
                            "bethe same for category %s" % record.name
                        )
                    )
        else:
            super(ProductCategory, self)._check_valuation_accouts()

    @api.onchange(
        "property_stock_valuation_account_id",
        "property_stock_account_output_categ_id",
        "property_stock_account_input_categ_id",
    )
    def _onchange_stock_accounts(self):
        """ only for Romania, stock_valuation output and input are the same
        """
        for record in self:
            if record.hide_stock_in_out_account:
                # is a romanian company:
                record.property_stock_account_input_categ_id = (
                    record.property_stock_valuation_account_id
                )
                record.property_stock_account_output_categ_id = (
                    record.property_stock_valuation_account_id
                )


class ProductTemplate(models.Model):
    _inherit = "product.template"

    property_stock_valuation_account_id = fields.Many2one(
        "account.account",
        "Stock Valuation Account",
        company_dependent=True,
        domain="[('company_id', '=', allowed_company_ids[0]),"
        "('deprecated', '=', False)]",
        check_company=True,
        help="In Romania accounting is only one account for valuation/input/"
        "output. If this value is set, we will use it, otherwise will "
        "use the category value. ",
    )

    def _get_product_accounts(self):
        accounts = super(ProductTemplate, self)._get_product_accounts()

        company = (
            self.env["res.company"].browse(self._context.get("force_company"))
            or self.env.company
        )
        if not company.romanian_accounting:
            return accounts

        property_stock_valuation_account_id = (
            self.property_stock_valuation_account_id
            or self.categ_id.property_stock_valuation_account_id
        )
        stock_picking_payable_account_id = (
            company.property_stock_picking_payable_account_id
        )
        stock_picking_receivable_account_id = (
            company.property_stock_picking_receivable_account_id
        )
        property_stock_usage_giving_account_id = (
            company.property_stock_usage_giving_account_id
        )
        if property_stock_valuation_account_id:
            accounts.update(
                {
                    "stock_input": property_stock_valuation_account_id,
                    "stock_output": property_stock_valuation_account_id,
                    "stock_valuation": property_stock_valuation_account_id,
                }
            )

        valued_type = self.env.context.get("valued_type", "indefinite")
        _logger.info(valued_type)

        # in nir si factura se ca utiliza 408
        if valued_type in [
            "reception_notice",
            "invoice_in_notice",
            "reception_notice_return",
        ]:
            if stock_picking_payable_account_id:
                accounts["stock_input"] = stock_picking_payable_account_id
        # in aviz si factura client se va utiliza 418
        elif valued_type == "invoice_out_notice":
            if stock_picking_receivable_account_id:
                accounts["stock_output"] = stock_picking_receivable_account_id
                accounts["stock_valuation"] = accounts["income"]
                accounts["income"] = stock_picking_receivable_account_id

        # in Romania iesirea din stoc de face de regula pe contul de cheltuiala
        elif valued_type in [
            "delivery",
            "delivery_notice",
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

        # suplimentar la darea in consum mai face o nota contabila
        elif valued_type == "usage_giving_secondary":
            accounts["stock_output"] = property_stock_usage_giving_account_id
            accounts["stock_input"] = property_stock_usage_giving_account_id
            accounts["stock_valuation"] = property_stock_usage_giving_account_id
        return accounts
