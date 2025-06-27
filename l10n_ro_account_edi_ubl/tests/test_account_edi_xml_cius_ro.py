from odoo.tests import tagged
from .common_data_setup import CiusRoTestSetup


@tagged("post_install", "-at_install")
class TestAccountEdiXmlCiusRo(CiusRoTestSetup):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tax_19_incas = cls.env["account.tax"].create(
            {
                "name": "tax_19_incas",
                "amount_type": "percent",
                "amount": 19,
                "type_tax_use": "sale",
                "sequence": 19,
                "company_id": cls.env.company.id,
                "tax_exigibility": "on_payment",
            }
        )

    def test_tax_with_valid_S(self):
        xml = """
        <Invoice>
          <cac:Item xmlns="x">
              <ID>S</ID><Percent>19</Percent>
            </cac:ClassifiedTaxCategory>
          </cac:Item>
        </Invoice>
        """
        self.partner.l10n_ro_vat_on_payment = True
        self.line.tax_ids = [(5, 0, 0)]
        self._run(xml)
        self.assertIn(self.tax_19_incas, self.line.tax_ids)

    def test_tax_category_S_without_vat_on_payment(self):
        xml = """
        <Invoice>
          <cac:Item xmlns="x">
            <cac:ClassifiedTaxCategory>
              <ID>S</ID><Percent>19</Percent>
            </cac:ClassifiedTaxCategory>
          </cac:Item>
        </Invoice>
        """
        self.partner.l10n_ro_vat_on_payment = False
        self.line.tax_ids = [(5, 0, 0)]
        self._run(xml)
        self.assertFalse(self.line.tax_ids)
