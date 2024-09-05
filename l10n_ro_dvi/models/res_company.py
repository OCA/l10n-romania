# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ro_property_vat_price_difference_product_id = fields.Many2one(
        "product.product",
        string="Romania - Vat Price Difference Product",
        domain="[('type', '=', 'service')]",
        help="This product will be used in create an accounting note "
        "for the difference between customs duty and bill",
    )

    def _l10n_ro_get_or_create_custom_duty_product(self):
        self.ensure_one()
        customs_duty_product = self.l10n_ro_property_customs_duty_product_id
        if not customs_duty_product:
            account = self.env["account.account"].search(
                [
                    ("code", "=", "446%"),
                    ("company_id", "=", self.id),
                ],
                limit=1,
            )

            customs_duty_product = self.env["product.product"].create(
                {
                    "name": _("Custom Duty"),
                    "categ_id": self.env.ref("product.product_category_all").id,
                    "type": "service",
                    "invoice_policy": "order",
                    "landed_cost_ok": True,
                    "property_account_expense_id": account if account else False,
                    "company_id": self.id,
                }
            )

            self.sudo().l10n_ro_property_customs_duty_product_id = customs_duty_product

        return customs_duty_product

    def _l10n_ro_get_or_create_customs_commission_product(self):
        self.ensure_one()
        customs_commission_product = self.l10n_ro_property_customs_commission_product_id
        if not customs_commission_product:
            account = self.env["account.account"].search(
                [
                    ("code", "=", "447%"),
                    ("company_id", "=", self.id),
                ],
                limit=1,
            )

            customs_commission_product = self.env["product.product"].create(
                {
                    "name": _("Customs Commission"),
                    "categ_id": self.env.ref("product.product_category_all").id,
                    "type": "service",
                    "invoice_policy": "order",
                    "landed_cost_ok": True,
                    "property_account_expense_id": account if account else False,
                    "company_id": self.id,
                }
            )

            self.sudo().l10n_ro_property_customs_commission_product_id = (
                customs_commission_product
            )

        return customs_commission_product

    def _l10n_ro_get_or_create_vat_price_difference_product(self):
        self.ensure_one()
        vat_price_diff_product = self.l10n_ro_property_vat_price_difference_product_id
        if not vat_price_diff_product:
            account = self.env["account.account"].search(
                [
                    ("code", "=", "658820"),
                    ("company_id", "=", self.id),
                ],
                limit=1,
            )
            vat_price_diff_product = self.env["product.product"].create(
                {
                    "name": "Vat price difference",
                    "categ_id": self.env.ref("product.product_category_all").id,
                    "type": "service",
                    "invoice_policy": "order",
                    "property_account_expense_id": account if account else False,
                    "company_id": self.id,
                }
            )

            self.sudo().l10n_ro_property_vat_price_difference_product_id = (
                vat_price_diff_product
            )

        return vat_price_diff_product
