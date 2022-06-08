# Copyright (C) 2022 NextERP Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

# Generare note contabile cu diferenta de pret

import logging

from odoo import fields
from odoo.tests import Form, tagged

from odoo.addons.l10n_ro_stock_account.tests.common import TestStockCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestStockCommon(TestStockCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        ro_template_ref = "l10n_ro.ro_chart_template"
        super(TestStockCommon, cls).setUpClass(chart_template_ref=ro_template_ref)

        cls.env.company.anglo_saxon_accounting = True
        cls.env.company.romanian_accounting = True
        cls.env.company.stock_acc_price_diff = True

        cls.env["account.move.line"]._get_or_create_price_difference_product()

    def create_invoice(self, diff_p1=0, diff_p2=0, quant_p1=0, quant_p2=0):
        invoice = Form(
            self.env["account.move"].with_context(
                default_move_type="in_invoice",
                default_invoice_date=fields.Date.today(),
                l10n_ro_approved_price_difference=True,
            )
        )
        invoice.partner_id = self.vendor
        invoice.purchase_id = self.po

        with invoice.invoice_line_ids.edit(0) as line_form:
            line_form.quantity += quant_p1
            line_form.price_unit += diff_p1
        with invoice.invoice_line_ids.edit(1) as line_form:
            line_form.quantity += quant_p2
            line_form.price_unit += diff_p2

        invoice = invoice.save()

        invoice.action_post()

        self.invoice = invoice
        _logger.info("Factura introdusa")
