import odoo

from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@odoo.tests.tagged("post_install", "-at_install")
class TestReportPoSOrder(TestPoSCommon):
    def setUp(self):
        super(TestReportPoSOrder, self).setUp()
        self.config = self.basic_config

    def test_wizard_report(self):
        wizard = self.env["pos.details.wizard"].create({})
        wizard.generate_report()

    def test_report_invoice(self):
        report_invoice = self.env["report.point_of_sale.report_invoice"].create({})
        report_invoice._get_report_values([], {})
