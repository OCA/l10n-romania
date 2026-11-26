# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models

# The delivery slip action's report. The document template it calls is
# ``stock.report_delivery_document``, but rendering always enters through the
# report whose ``report_name`` is ``stock.report_deliveryslip`` (the pdf action
# and its html variant share it), so flagging this one name covers both.
L10N_RO_PICKING_REPORT_NAMES = {
    "stock.report_deliveryslip",
}


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _l10n_ro_picking_report_env(self, report_ref):
        """Flag the delivery slip so a RO company prints it in Romanian.

        The language is chosen by ``stock.picking._get_report_lang``, which
        reads this flag. Scoping the flag to the delivery slip keeps every other
        report on the partner's language, and the ``country_id`` guard in
        ``_get_report_lang`` keeps non-RO companies untouched."""
        try:
            report = self._get_report(report_ref)
        except ValueError:
            return self
        if report.report_name in L10N_RO_PICKING_REPORT_NAMES:
            return self.with_context(l10n_ro_force_picking_report_lang=True)
        return self

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        report = self._l10n_ro_picking_report_env(report_ref)
        return super(IrActionsReport, report)._render_qweb_pdf(
            report_ref, res_ids=res_ids, data=data
        )

    def _render_qweb_html(self, report_ref, docids, data=None):
        report = self._l10n_ro_picking_report_env(report_ref)
        return super(IrActionsReport, report)._render_qweb_html(
            report_ref, docids, data=data
        )
