# Copyright (C) 2020 OdooERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SalePurchaseJournalReport(models.TransientModel):
    _name = "l10n.ro.account.report.journal"
    _description = "Sale Purchase Journal Report"

    company_id = fields.Many2one(
        "res.company",
        "Company",
        required=True,
        default=lambda self: self.env.company,
        domain="[('country_id', '=', self.env.ref('base.ro'))]",
        help="Will only show companies with country Romania",
    )
    journal = fields.Selection(
        selection=[
            ("purchase", "Purchase = In invoices"),
            ("sale", "Sale = Out invoices"),
        ],
        string="Journal type",
        default="sale",
        required=True,
    )
    date_range_id = fields.Many2one(
        comodel_name="date.range",
        string="Date range",
        domain="['|',('company_id','=',company_id)," "('company_id','=',False)]",
        help="If you select this, the date_from ant to will be taken from "
        "this and will not be editable",
    )
    date_from = fields.Date(
        "Start Date",
        required=True,
        default=fields.Date.today() - relativedelta(months=1, day=1),
    )
    date_to = fields.Date(
        "End Date",
        required=True,
        default=fields.Date.today() - relativedelta(day=1, days=-1),
    )
    show_warnings = fields.Boolean(
        "Show Warnings",
        default=1,
        help="if you check this, you will have another column that is going "
        "to show you errors/warnings if exist",
    )

    @api.onchange("date_range_id")
    def onchange_date_range_id(self):
        """Handle date range change."""
        if self.date_range_id:
            self.date_from = self.date_range_id.date_start
            self.date_to = self.date_range_id.date_end

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for fy in self:
            # Starting date must be prior to the ending date
            date_from = fy.date_from
            date_to = fy.date_to
            if date_to < date_from:
                raise ValidationError(
                    _("The ending date must not be prior to the starting " "date.")
                )

    def print_report_html(self):
        res = self.print_report(html=True)
        return res

    def print_report(self, html=False):
        self.ensure_one()
        [data] = self.read()
        datas = {"ids": [], "model": "l10n_ro_account_report_journal", "form": data}
        if self.journal == "sale":
            report_action = "l10n_ro_account_report_journal.action_report_sale" + (
                "_html" if html else ""
            )
        else:
            report_action = "l10n_ro_account_report_journal.action_report_sale" + (
                "_html" if html else ""
            )
        ref = self.env.ref(report_action)
        res = ref.report_action(docids=[], data=datas, config=False)
        return res
