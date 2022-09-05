# ©  2022 NexERP Romania
# ©  2008-2020 Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details

import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class AccountInvoiceDVI(models.TransientModel):
    _name = "account.invoice.dvi"
    _description = "account.invoice.dvi"

    date = fields.Date("Date")
    currency_id = fields.Many2one(
        "res.currency", readonly=1, help="is invoice company currency"
    )
    total_tax_value = fields.Monetary(
        compute="_compute_total_tax_value",
        readonly=1,
        help="Is readonly sum of product tax and custom tax."
        "This must be the tax value that you have on dvi",
    )

    custom_duty_product = fields.Many2one(
        "product.product",
        help="A product type service with l10n_ro_custom_duty checked"
        " (purchase tab).  Journal entry for commision will be with this product &"
        " default vat for custom duty and invoice - to find it in declaration based on tags",
    )
    custom_duty_tax_id = fields.Many2one(
        "account.tax", help="If set will compute VAT from custom_duty_value "
    )
    custom_duty_value = fields.Monetary(help="This is a value from received dvi")
    custom_duty_tax_value = fields.Monetary(
        readonly=1,
        compute="_compute_total_tax_value",
        help="readonly computed tax from custom_duty_value",
    )

    custom_commision_product = fields.Many2one(
        "product.product",
        help="Product type service with l10n_ro_custom_commision checed "
        "(in purchase tab). Journal entry for commision will be with this product",
    )
    custom_commission_value = fields.Monetary(help="taken from dvi if exists")

    invoice_value = fields.Monetary(readonly=1, help="Inovice value without taxes")
    invoice_tax_id = fields.Many2one(
        "account.tax",
        help="Is the vat that is paid in custom for products."
        " default is taken from custom duty tax"
        ". will put this vat tag in journal entry to find it in reports",
    )
    invoice_tax_value = fields.Monetary(
        help="default is computed as tax_id from product;"
        " is not recomputed based on selected vat"
    )

    @api.model
    def default_get(self, fields_list):
        defaults = super(AccountInvoiceDVI, self).default_get(fields_list)
        active_id = self.env.context.get("active_id", False)
        invoice = self.env["account.move"].browse(active_id)
        if not invoice.company_id.l10n_ro_accounting:
            raise ValidationError(_("This is only for Romanian accounting"))
        defaults["currency_id"] = invoice.company_id.currency_id.id
        defaults["date"] = invoice.invoice_date or fields.Date.today()

        custom_duty_product = self.env["product.product"].search(
            [("l10n_ro_custom_duty", "=", True)], limit=1
        )
        defaults["custom_duty_product"] = custom_duty_product.id

        custom_commision = self.env["product.product"].search(
            [("l10n_ro_custom_commision", "=", True)], limit=1
        )
        defaults["custom_commision_product"] = custom_commision.id

        tax_id = custom_duty_product.supplier_taxes_id[0]
        defaults["invoice_tax_id"] = defaults["custom_duty_tax_id"] = tax_id.id
        tax_values = tax_id.compute_all(abs(invoice.amount_untaxed_signed))

        defaults["invoice_value"] = tax_values["total_excluded"]
        defaults["invoice_tax_value"] = (
            tax_values["total_included"] - tax_values["total_excluded"]
        )
        return defaults

    @api.depends("invoice_tax_value", "custom_duty_tax_id", "custom_duty_value")
    def _compute_total_tax_value(self):
        for rec in self:
            if rec.custom_duty_value and rec.custom_duty_tax_id:
                tax_values = rec.custom_duty_tax_id.compute_all(rec.custom_duty_value)
                rec.custom_duty_tax_value = (
                    tax_values["total_included"] - tax_values["total_excluded"]
                )
            else:
                rec.custom_duty_tax_value = 0

            rec.total_tax_value = rec.invoice_tax_value + rec.custom_duty_tax_value

    def do_create_dvi(self):
        self.ensure_one()
        active_id = self.env.context.get("active_id", False)
        invoice = self.env["account.move"].browse(active_id)
        if not invoice.company_id.l10n_ro_accounting:
            raise ValidationError(_("This button is only for Romanian accounting"))

        pickings = self.env["stock.picking"]

        for line in invoice.invoice_line_ids:
            pickings |= line.purchase_line_id.order_id.picking_ids.filtered(
                lambda p: p.state == "done"
            )
        values = {
            "date": self.date,
            "l10n_ro_landed_type": "dvi",
            "picking_ids": [(6, 0, pickings.ids)],
            "cost_lines": [],
            "account_journal_id": invoice.journal_id.id,
            "l10n_ro_tax_id": self.invoice_tax_id.id,
            "l10n_ro_tax_value": self.total_tax_value,
            "vendor_bill_id": active_id,
        }
        if self.custom_duty_value:
            if not self.custom_duty_product:
                raise ValidationError(
                    _(
                        "You must have a custom duty product to be able to put the custom duty"
                    )
                )
            accounts_data = (
                self.custom_duty_product.product_tmpl_id.get_product_accounts()
            )
            values["cost_lines"] += [
                (
                    0,
                    0,
                    {
                        "name": self.custom_duty_product.name,
                        "product_id": self.custom_duty_product.id,
                        "price_unit": self.custom_duty_value,
                        "split_method": "by_current_cost_price",
                        "account_id": accounts_data["expense"].id,
                        "l10n_ro_tax_id": self.custom_duty_tax_id.id,
                    },
                )
            ]

        if self.custom_commission_value:
            if not self.custom_commision_product:
                raise ValidationError(
                    _(
                        "You must have a custom commision product to be able to put"
                        " the custom commision."
                    )
                )
            accounts_data = (
                self.custom_commision_product.product_tmpl_id.get_product_accounts()
            )
            values["cost_lines"] += [
                (
                    0,
                    0,
                    {
                        "name": self.custom_commision_product.name,
                        "product_id": self.custom_commision_product.id,
                        "price_unit": self.custom_commission_value,
                        "split_method": "by_current_cost_price",
                        "account_id": accounts_data["expense"].id,
                    },
                )
            ]

        landed_cost = self.env["stock.landed.cost"].create(values)

        action = self.env.ref("stock_landed_costs.action_stock_landed_cost")
        action = action.read()[0]

        action["views"] = [(False, "form")]
        action["res_id"] = landed_cost.id
        return action
