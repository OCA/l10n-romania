# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ProductCategory(models.Model):
    _inherit = "product.category"

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
        ro_chart = self.env.ref("l10n_ro.ro_chart_template", raise_if_not_found=False)

        if self.env.company.chart_template_id == ro_chart:
            return
        else:
            self.super(ProductCategory, self)._check_valuation_accouts()


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

        property_stock_valuation_account_id = (
            self.property_stock_valuation_account_id
            or self.categ_id.property_stock_valuation_account_id
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
        if valued_type in ["reception_notice", "invoice_in_notice"]:
            stock_picking_payable_account_id = (
                self.env.user.company_id.property_stock_picking_payable_account_id
            )
            if stock_picking_payable_account_id:
                accounts[
                    "stock_input"
                ] = stock_picking_payable_account_id  # pt contabilitatea anglo-saxona
                # accounts['expense'] = stock_picking_payable_account_id       # pentru contabilitate continentala

        elif valued_type == "invoice_out_notice":
            stock_picking_receivable_account_id = (
                self.env.user.company_id.property_stock_picking_receivable_account_id
            )
            if stock_picking_receivable_account_id:
                accounts["stock_output"] = stock_picking_receivable_account_id
                accounts["stock_valuation"] = accounts["income"]
                accounts["income"] = stock_picking_receivable_account_id

        # la inventatiere
        elif valued_type in ["plus_inventory"]:
            accounts["stock_input"] = accounts["expense"]
            accounts["stock_output"] = accounts["expense"]

        # la inventatiere
        elif valued_type in ["minus_inventory"]:
            accounts["stock_output"] = accounts["expense"]
            accounts["stock_input"] = accounts["expense"]

        # la vanzare se scoate stocul pe cheltuiala
        elif valued_type in ["delivery", "delivery_notice"]:
            accounts["stock_output"] = accounts["expense"]

        return accounts
