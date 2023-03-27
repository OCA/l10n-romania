# Copyright (C) 2018 Forest and Biomass Romania
# Copyright (C) 2019 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class WizardAccountPeriodClosing(models.TransientModel):
    _name = "l10n.ro.account.period.closing.wizard"
    _description = "Wizard for Account Period Closing"

    def _get_default_date_from(self):
        today = fields.Date.from_string(fields.Date.today())
        return today + relativedelta(day=1, months=-1)

    def _get_default_date_to(self):
        today = fields.Date.from_string(fields.Date.today())
        return today + relativedelta(day=1, days=-1)

    closing_id = fields.Many2one(
        "l10n.ro.account.period.closing",
        "Closing Model",
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        comodel_name="res.company", related="closing_id.company_id"
    )
    journal_id = fields.Many2one(comodel_name="account.journal")
    date_from = fields.Date("Start Date", required=True, default=_get_default_date_from)
    date_to = fields.Date("End Date", required=True, default=_get_default_date_to)

    @api.onchange("closing_id")
    def onchange_closing_id(self):
        """Handle closing_id change."""
        if self.closing_id:
            self.journal_id = self.closing_id.journal_id

    def do_close(self):
        for wizard in self:
            wizard.closing_id.close(
                wizard.journal_id.id, wizard.date_from, wizard.date_to
            )
        return {"type": "ir.actions.act_window_close"}
