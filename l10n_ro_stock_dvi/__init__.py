from odoo import SUPERUSER_ID, _, api

from . import models, wizard


def _post_init_hook_create_dvi_products(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    romanian_companies = env["res.company"].search([("l10n_ro_accounting", "=", True)])
    if not romanian_companies:
        return
    custom_duty_product = env["product.template"].create(
        {
            "name": _("Romanian Custom Duty"),
            "type": "service",
            "invoice_policy": "order",
            "taxes_id": False,
            "company_id": False,
            "sale_ok": False,
            "l10n_ro_custom_duty": True,
        }
    )

    custom_commision_product = env["product.template"].create(
        {
            "name": _("Romanian Customs Commission"),
            "type": "service",
            "invoice_policy": "order",
            "taxes_id": False,
            "supplier_taxes_id": False,
            "sale_ok": False,
            "company_id": False,
            "l10n_ro_custom_commision": True,
        }
    )

    # add the property_account_expense & purchase tax for romanian companies
    for company in romanian_companies:
        domain = [("code", "=like", "446%"), ("company_id", "=", company.id)]
        to_write = {
            "property_account_expense_id": env["account.account"]
            .search(domain, limit=1)
            .id,
        }
        supplier_taxes_id = env["account.tax"].search(
            [
                ("type_tax_use", "=", "purchase"),
                ("name", "ilike", "deductibil 19%"),
                ("company_id", "=", company.id),
            ],
            limit=1,
        )
        if supplier_taxes_id:
            to_write["supplier_taxes_id"] = [(4, supplier_taxes_id.id, 0)]
        custom_duty_product.with_company(company).write(to_write)
        domain = [("code", "=like", "447%"), ("company_id", "=", company.id)]
        custom_commision_product.with_company(company).write(
            {
                "property_account_expense_id": env["account.account"]
                .search(domain, limit=1)
                .id
            }
        )
