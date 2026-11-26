# Copyright (C) 2026 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models

_LANDSCAPE_PF = (
    "l10n_ro_stock_account_retail_picking_report.paperformat_retail_nir_landscape"
)


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def get_paperformat(self):
        # When the delivery slip is a shop reception, print it on landscape so
        # the extra retail columns fit; the depot NIR and the aviz stay on the
        # company's default (portrait) format.
        pf_xmlid = self.env.context.get("l10n_ro_retail_landscape_pf")
        if pf_xmlid:
            paperformat = self.env.ref(pf_xmlid, raise_if_not_found=False)
            if paperformat:
                return paperformat
        return super().get_paperformat()

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        report = self._get_report(report_ref)
        if report.report_name == "stock.report_deliveryslip" and res_ids:
            pickings = self.env["stock.picking"].browse(res_ids).exists()
            if pickings and all(p.l10n_ro_retail_incoming for p in pickings):
                self = self.with_context(l10n_ro_retail_landscape_pf=_LANDSCAPE_PF)
        return super()._render_qweb_pdf_prepare_streams(
            report_ref, data, res_ids=res_ids
        )
