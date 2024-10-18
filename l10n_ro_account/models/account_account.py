# Copyright (C) 2018 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class Account(models.Model):
    _inherit = "account.account"

    l10n_ro_external_code = fields.Char(
        compute="_compute_l10n_ro_external_code", store=True
    )

    @api.depends("code")
    def _compute_l10n_ro_external_code(self):
        for account in self:
            account.l10n_ro_external_code = account.internal_to_external()

    def external_code_to_internal(self, code):
        account_id = False
        if "." in code:
            odoo_code, analytic = code.split(".")
            odoo_code = (odoo_code + "00000")[:4] + analytic.zfill(2)
        else:
            odoo_code = (code + "00000")[:6]
        account = self.env["account.account"].search([("code", "=", odoo_code)])
        if len(account) == 1:
            account_id = account.id
        return account_id

    def internal_to_external(self):
        if not self.code or len(self.code) < 4:
            return self.code
        cont = self.code[:4]
        while cont and cont[-1] == "0":
            cont = cont[:-1]
        try:
            analitic = int(self.code[4:])
        except Exception:
            analitic = self.code[4:]
        if analitic:
            cont += "." + str(analitic)
        return cont

    def _compute_display_name(self):
        rest = self
        for account in self:
            if self.env.company.l10n_ro_accounting:
                code = account.l10n_ro_external_code or account.code
                name = code + " " + account.name
                account.display_name = name
                rest -= account
        return super(Account, rest)._compute_display_name()
