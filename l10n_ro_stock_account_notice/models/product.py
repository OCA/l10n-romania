# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = ["product.template", "l10n.ro.mixin"]

    def _get_product_accounts(self):
        accounts = super()._get_product_accounts()

        company = (
            self.env["res.company"].browse(self._context.get("force_company"))
            or self.env.company
        )
        if not self.env["res.company"]._check_is_l10n_ro_record(company.id):
            return accounts

        stock_picking_payable_account_id = (
            company.l10n_ro_property_stock_picking_payable_account_id
        )
        stock_picking_receivable_account_id = (
            company.l10n_ro_property_stock_picking_receivable_account_id
        )

        valued_type = self.env.context.get("valued_type", "indefinite")

        if self.type != "service" and valued_type == "in_invoice":
            accounts["expense"] = accounts["stock_valuation"]

        # in nir si factura se ca utiliza 408
        if valued_type in [
            "reception_notice",
            "invoice_in_notice",
        ]:
            if stock_picking_payable_account_id:
                accounts["stock_input"] = stock_picking_payable_account_id
                accounts["expense"] = stock_picking_payable_account_id
        elif valued_type in [
            "reception_notice_return",
        ]:
            if stock_picking_payable_account_id:
                accounts["stock_input"] = stock_picking_payable_account_id
                accounts["stock_output"] = stock_picking_payable_account_id
                accounts["expense"] = stock_picking_payable_account_id
        # in aviz si factura client se va utiliza 418
        elif valued_type == "invoice_out_notice":
            if stock_picking_receivable_account_id:
                accounts["stock_output"] = stock_picking_receivable_account_id
                accounts["stock_valuation"] = accounts["income"]
                accounts["income"] = stock_picking_receivable_account_id

        # in Romania iesirea din stoc de face de regula pe contul de cheltuiala
        elif valued_type in ["delivery_notice"]:
            accounts["stock_output"] = accounts["expense"]
        elif valued_type in ["delivery_notice_return"]:
            accounts["stock_input"] = accounts["stock_output"] = accounts["expense"]
        elif valued_type in ["dropshipped"]:
            if stock_picking_payable_account_id:
                accounts["stock_input"] = stock_picking_payable_account_id
            accounts["stock_output"] = accounts["expense"]
        return accounts
