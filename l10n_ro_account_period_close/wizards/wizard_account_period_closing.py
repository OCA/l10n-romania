# Copyright  2018 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class WizardAccountPeriodClosing(models.TransientModel):
    _name = "account.period.closing.wizard"
    _description = "Wizard for Account Period Closing"

    def _get_default_date_from(self):
        today = fields.Date.from_string(fields.Date.today())
        return today + relativedelta(day=1, months=-1)

    def _get_default_date_to(self):
        today = fields.Date.from_string(fields.Date.today())
        return today + relativedelta(day=1, days=-1)

    closing_id = fields.Many2one(
        "account.period.closing",
        "Closing Model",
        required=True,
        ondelete="cascade"
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        related="closing_id.company_id")
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        related="closing_id.journal_id")
    date_range_id = fields.Many2one(
        comodel_name="date.range",
        string="Date range")
    date_from = fields.Date("Start Date", required=True,
                            default=_get_default_date_from)
    date_to = fields.Date("End Date", required=True,
                          default=_get_default_date_to)

    @api.onchange('date_range_id')
    def onchange_date_range_id(self):
        """Handle date range change."""
        if self.date_range_id:
            self.date_from = self.date_range_id.date_start
            self.date_to = self.date_range_id.date_end

    @api.multi
    def do_close(self):
        self.ensure_one()
        self.closing_id.close(self.date_from, self.date_to)
        return {'type': 'ir.actions.act_window_close'}
