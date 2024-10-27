from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestReportPoSOrder(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country("ro")
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.anglo_saxon_accounting = True
        cls.env.company.l10n_ro_accounting = True

    def test_wizard_report(self):
        wizard = self.env["pos.details.wizard"].create({})
        wizard.generate_report()

    def test_report_saledetails(self):
        report_saledetails = self.env["report.point_of_sale.report_saledetails"]
        report_saledetails.get_sale_details()

    def test_report_invoice(self):
        report_invoice = self.env["report.point_of_sale.report_invoice"].sudo()
        report_invoice._get_report_values([], {})
