# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


from odoo import api, fields, models


class ActivityStatementWizard(models.TransientModel):
    """Activity Statement wizard."""

    _inherit = "activity.statement.wizard"

    @api.model
    def _get_date_start(self):
        return fields.Date.context_today(self).replace(day=1, month=1)

    date_start = fields.Date(required=True, default=_get_date_start)
    show_debit_credit = fields.Boolean("Show Debit Credit")

    @api.onchange("aging_type")
    def onchange_aging_type(self):
        super().onchange_aging_type()
        self.date_start = self.date_end.replace(day=1, month=1)

    def _prepare_statement(self):
        values = super(ActivityStatementWizard, self)._prepare_statement()
        values["show_debit_credit"] = self.show_debit_credit
        return values
