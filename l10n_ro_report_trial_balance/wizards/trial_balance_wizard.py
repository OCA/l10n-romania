# Copyright (C) 2018 FOREST AND BIOMASS ROMANIA SA
# Copyright (C) 2021 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class RomaniaTrialBalanceReportWizard(models.TransientModel):
    """Trial balance report wizard."""

    _name = "l10n.ro.report.trial.balance.wizard"
    _inherit = "trial.balance.report.wizard"
    _description = "Romania Trial Balance Report Wizard"

    show_off_balance_accounts = fields.Boolean("Print Off Balance Accounts")

    def _prepare_report_trial_balance(self):
        res = super()._prepare_report_trial_balance()
        res["show_off_balance_accounts"] = self.show_off_balance_accounts
        return res

    def _print_report(self, report_type):
        self.ensure_one()
        data = self._prepare_report_trial_balance()
        if report_type == "xlsx":
            report_name = "l10n_ro_report_trial_balance_xlsx"
        else:
            report_name = "l10n_ro_report_trial_balance.trial_balance"
        return (
            self.env["ir.actions.report"]
            .search(
                [("report_name", "=", report_name), ("report_type", "=", report_type)],
                limit=1,
            )
            .report_action(self, data=data)
        )
