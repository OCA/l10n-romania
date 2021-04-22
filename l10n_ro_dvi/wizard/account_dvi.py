# Copyright (C) 2020 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


from odoo import _, api, fields, models


class AccountInvoiceDVI(models.TransientModel):
    _name = "account.invoice.dvi"
    _description = "account.invoice.dvi"

    date = fields.Date("Date")
    custom_duty = fields.Monetary(string="Custom Duty")  # costuri vamale
    customs_commission = fields.Monetary(string="Customs Commission")  # comision vamal
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id
    )

    tax_value = fields.Monetary()
    tax_id = fields.Many2one("account.tax")  # TVA platit in Vama

    def _prepare_custom_duty_product(self):

        domain = [("code", "=like", "446%")]
        account = self.env["account.account"].search(domain, limit=1)
        return {
            "name": _("Custom Duty"),
            "type": "service",
            "invoice_policy": "order",
            "property_account_expense_id": account.id,
            "taxes_id": False,
            "company_id": False,
        }

    def _prepare_customs_commission_product(self):

        domain = [("code", "=like", "447%")]
        account = self.env["account.account"].search(domain, limit=1)
        return {
            "name": _("Customs Commission"),
            "type": "service",
            "invoice_policy": "order",
            "property_account_expense_id": account.id,
            "taxes_id": False,
            "company_id": False,
        }

    @api.model
    def get_custom_duty_product(self):
        product_id = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("dvi.custom_duty_product_id")
        )
        return self.env["product.product"].browse(int(product_id)).exists()

    @api.model
    def get_customs_commission_product(self):
        product_id = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("dvi.customs_commission_product_id")
        )
        return self.env["product.product"].browse(int(product_id)).exists()

    @api.model
    def default_get(self, fields_list):
        defaults = super(AccountInvoiceDVI, self).default_get(fields_list)
        active_id = self.env.context.get("active_id", False)
        invoice = self.env["account.move"].browse(active_id)
        defaults["date"] = invoice.invoice_date or fields.Date.today()
        tax_id = self.env.company.account_purchase_tax_id
        defaults["tax_id"] = tax_id.id
        tax_values = tax_id.compute_all(abs(invoice.amount_untaxed_signed))
        defaults["tax_value"] = (
            tax_values["total_included"] - tax_values["total_excluded"]
        )
        return defaults

    def do_create_dvi(self):
        active_id = self.env.context.get("active_id", False)
        invoice = self.env["account.move"].browse(active_id)

        pickings = self.env["stock.picking"]

        for line in invoice.invoice_line_ids:
            pickings |= line.purchase_line_id.order_id.picking_ids

        # determinare produse utilizate la landed cost
        values = {
            "date": self.date,
            "landed_type": "dvi",
            "picking_ids": [(6, 0, pickings.ids)],
            "cost_lines": [],
            "account_journal_id": invoice.journal_id.id,
            "tax_id": self.tax_id.id,
            "tax_value": self.tax_value,
        }
        config_parameter = self.env["ir.config_parameter"].sudo()
        if self.custom_duty:

            custom_duty_product = self.get_custom_duty_product()
            if not custom_duty_product:
                vals = self._prepare_custom_duty_product()
                custom_duty_product = self.env["product.product"].create(vals)
                config_parameter.set_param(
                    "dvi.custom_duty_product_id", custom_duty_product.id
                )
            accounts_data = custom_duty_product.product_tmpl_id.get_product_accounts()

            values["cost_lines"] += [
                (
                    0,
                    0,
                    {
                        "name": custom_duty_product.name,
                        "product_id": custom_duty_product.id,
                        "price_unit": self.custom_duty,
                        "split_method": "by_current_cost_price",
                        "account_id": accounts_data["expense"].id,
                    },
                )
            ]

        if self.customs_commission:

            customs_commission_product = self.get_customs_commission_product()
            if not customs_commission_product:
                vals = self._prepare_customs_commission_product()
                customs_commission_product = self.env["product.product"].create(vals)
                config_parameter.set_param(
                    "dvi.customs_commission_product_id", customs_commission_product.id
                )
            accounts_data = (
                customs_commission_product.product_tmpl_id.get_product_accounts()
            )

            values["cost_lines"] += [
                (
                    0,
                    0,
                    {
                        "name": customs_commission_product.name,
                        "product_id": customs_commission_product.id,
                        "price_unit": self.customs_commission,
                        "split_method": "by_current_cost_price",
                        "account_id": accounts_data["expense"].id,
                    },
                )
            ]

        landed_cost = self.env["stock.landed.cost"].create(values)
        invoice.write({"dvi_id": landed_cost.id})

        action = self.env.ref("stock_landed_costs.action_stock_landed_cost")
        action = action.read()[0]

        action["views"] = [(False, "form")]
        action["res_id"] = landed_cost.id

        return action
