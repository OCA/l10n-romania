# Copyright (C) 2018 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class Account(models.Model):
    _inherit = "account.account"

    l10n_ro_external_code = fields.Char(
        compute="_compute_l10n_ro_external_code", store=False
    )

    @api.depends_context("company")
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
        if self.code and not self.code.isdigit():
            return self.code
        if not self.code or len(self.code) < 4:
            return self.code
        cont = self.code[:4]
        while cont and cont[-1] == "0":
            cont = cont[:-1]
        if self.code[4:]:
            analytic = int(self.code[4:])
            if analytic:
                cont += "." + str(analytic)
        return cont

    def _l10n_ro_get_display_company(self):
        """Compania din care se citeste codul contului (code e company_dependent).
        Prioritate: compania curenta, apoi prima companie activa a contului,
        apoi prima companie a contului."""
        self.ensure_one()
        company = self.env.company
        if not self.company_ids or company in self.company_ids:
            # compania curenta
            return company
        # prima companie activa a contului, altfel prima companie a contului
        allowed = self.company_ids & self.env.companies
        return allowed[:1] or self.company_ids[:1]

    @api.depends_context("company", "allowed_company_ids", "formatted_display_name")
    @api.depends("code")
    def _compute_display_name(self):
        rest = self
        for account in self:
            company = account._l10n_ro_get_display_company()
            if company.l10n_ro_accounting:
                account_cmp = account.with_company(company)
                code = account_cmp.l10n_ro_external_code or account_cmp.code
                if code and account.name:
                    name = code + " " + account.name
                    account.display_name = name
                    rest -= account
        return super(Account, rest)._compute_display_name()
