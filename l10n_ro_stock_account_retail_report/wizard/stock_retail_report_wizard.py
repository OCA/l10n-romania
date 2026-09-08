# Copyright (C) 2026 NextERP Romania
# Copyright (C) 2026 Dakai Soft SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class StockRetailReportWizard(models.TransientModel):
    """Ask for the period, then open the retail stock report over it.

    Reconciling a shop against the trial balance means picking a moment and
    comparing three figures: 371, 378 and 4428. The report answers for that
    moment when it is given one, so the wizard exists to give it one.
    """

    _name = "l10n.ro.stock.retail.report.wizard"
    _description = "Retail Stock Report Period"

    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    date_from = fields.Date(
        string="From",
        required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1),
        help="Movements before this date are folded into the opening balance.",
    )
    date_to = fields.Date(
        string="To",
        required=True,
        default=fields.Date.context_today,
        help="The closing balance is the position at the end of this day - the "
        "figure to compare against the trial balance.",
    )
    warehouse_ids = fields.Many2many(
        "stock.warehouse",
        string="Shops",
        domain="[('l10n_ro_retail', '=', True), ('company_id', '=', company_id)]",
        help="Leave empty for every retail warehouse of the company.",
    )

    @api.onchange("date_from")
    def _onchange_date_from(self):
        for wizard in self:
            if wizard.date_to and wizard.date_from > wizard.date_to:
                wizard.date_to = wizard.date_from + relativedelta(day=31)

    def action_open_report(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(self.env._("The start of the period is after its end."))
        domain = [("company_id", "=", self.company_id.id)]
        if self.warehouse_ids:
            domain.append(("warehouse_id", "in", self.warehouse_ids.ids))
        action = self.env["ir.actions.actions"]._for_xml_id(
            "l10n_ro_stock_account_retail_report.action_stock_retail_report"
        )
        action.update(
            {
                "domain": domain,
                "display_name": self.env._(
                    "Retail Stock %(date_from)s - %(date_to)s",
                    date_from=fields.Date.to_string(self.date_from),
                    date_to=fields.Date.to_string(self.date_to),
                ),
                "context": {
                    **self.env.context,
                    # Dates, plainly. The ledger carries the accounting date
                    # of the entry each row belongs to, so the period is read
                    # the way an accounting period is: the last day included,
                    # and no timezone in the middle to shift a shop's evening
                    # sales into the day before.
                    "l10n_ro_retail_date_from": fields.Date.to_string(self.date_from),
                    "l10n_ro_retail_date_to": fields.Date.to_string(self.date_to),
                    "search_default_group_warehouse": 1,
                },
            }
        )
        return action
