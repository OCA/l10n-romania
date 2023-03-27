# Copyright 2018 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartnerBank(models.Model):
    _name = "res.partner.bank"
    _inherit = ["res.partner.bank", "l10n.ro.mixin"]

    l10n_ro_print_report = fields.Boolean(string="Romania - Print in Report")

    _sql_constraints = [
        ("unique_number", "CHECK(1=1)", "Account Number must be unique"),
    ]

    @api.constrains("sanitized_acc_number")
    def _check_sanitized_acc_number(self):
        for bank in self:
            if bank.company_id.l10n_ro_accounting:
                account = self.env["res.partner.bank"].search(
                    [
                        ("sanitized_acc_number", "=", bank.sanitized_acc_number),
                        ("company_id", "=", bank.company_id.id),
                        ("partner_id", "=", bank.partner_id.id),
                        ("id", "!=", bank.id),
                    ]
                )
                if account:
                    raise ValidationError(_("Account Number must be unique"))
            else:
                account = self.env["res.partner.bank"].search(
                    [
                        ("sanitized_acc_number", "=", bank.sanitized_acc_number),
                        ("company_id", "=", bank.company_id.id),
                        ("id", "!=", bank.id),
                    ]
                )
                if account:
                    raise ValidationError(_("Account Number must be unique"))
        return True
