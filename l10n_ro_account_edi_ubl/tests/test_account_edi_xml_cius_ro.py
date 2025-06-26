from xml.etree import ElementTree as ET
from odoo.tests.common import TransactionCase

# -*- coding: utf-8 -*-

class TestImportFillInvoiceLineFormExtra(TransactionCase):

    def setUp(self):
        super().setUp()
        self.service = self.env['account.edi.xml.cius_ro']
        acc = self.env['account.account'].search([], limit=1)
        if not acc:
            acc = self.env['account.account'].create({
                'name': 'Test Account',
                'code': 'TA',
                'user_type_id': self.env.ref('account.data_account_type_expenses').id,
                'company_id': self.env.company.id,
            })
        self.journal = self.env['account.journal'].create({
            'name': 'Test Purchase Journal',
            'type': 'purchase',
            'default_account_id': acc.id,
            'company_id': self.env.company.id,
        })
        self.partner = self.env['res.partner'].create({
            'name': 'Vendor Co', 'is_company': True
        })
        self.invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'journal_id': self.journal.id,
            'partner_id': self.partner.id,
        })
        self.line = self.env['account.move.line'].create({
            'move_id': self.invoice.id,
            'account_id': acc.id,
            'name': 'Line Test',
            'quantity': 1.0,
            'price_unit': 50.0,
        })

    def _run(self, xml_str):
        tree = ET.fromstring(xml_str)
        return self.service._import_fill_invoice_line_form(
            self.journal, tree, self.invoice, self.line, 1.0
        )

    def test_standard_item_identification(self):
        xml = """
        <Invoice>
          <cac:Item xmlns:cac="x" xmlns:cbc="x">
            <cac:StandardItemIdentification>
              <cbc:ID>STD123</cbc:ID>
            </cac:StandardItemIdentification>
          </cac:Item>
        </Invoice>
        """
        tmpl = self.env['product.template'].create({'name': 'TP'})
        prod = self.env['product.product'].create({
            'name': 'TP', 'product_tmpl_id': tmpl.id
        })
        self.env['product.supplierinfo'].create({
            'product_tmpl_id': tmpl.id,
            'product_code': 'STD123',
            'name': self.partner.id,
        })
        self._run(xml)
        self.assertEqual(self.line.l10n_ro_vendor_code, 'STD123')
        self.assertEqual(self.line.product_id, prod)

    def test_vendor_code_no_matching_product(self):
        xml = """
        <Invoice>
          <cac:Item xmlns:cac="x" xmlns:cbc="x">
            <cac:SellersItemIdentification>
              <cbc:ID>NOEXIST</cbc:ID>
            </cac:SellersItemIdentification>
          </cac:Item>
        </Invoice>
        """
        tmpl = self.env['product.template'].create({'name': 'X'})
        other = self.env['product.product'].create({
            'name': 'X', 'product_tmpl_id': tmpl.id
        })
        self.line.product_id = other
        self._run(xml)
        self.assertEqual(self.line.l10n_ro_vendor_code, 'NOEXIST')
        self.assertEqual(self.line.product_id, other)

    def test_multiple_tax_categories_ignored(self):
        xml = """
        <Invoice>
          <cac:Item xmlns="x">
            <cac:ClassifiedTaxCategory>
              <ID>O</ID><Percent>0</Percent>
            </cac:ClassifiedTaxCategory>
            <cac:ClassifiedTaxCategory>
              <ID>S</ID><Percent>5</Percent>
            </cac:ClassifiedTaxCategory>
          </cac:Item>
        </Invoice>
        """
        self.line.tax_ids = [(5, 0, 0)]
        self._run(xml)
        self.assertFalse(self.line.tax_ids)

    def test_tax_category_E_adds_zero_tax(self):
        xml = """
        <Invoice>
          <cac:Item xmlns="x">
            <cac:ClassifiedTaxCategory>
              <ID>E</ID><Percent>19</Percent>
            </cac:ClassifiedTaxCategory>
          </cac:Item>
        </Invoice>
        """
        tax0 = self.env['account.tax'].create({
            'name': 'ZeroTax', 'amount': 0.0,
            'type_tax_use': 'purchase', 'amount_type': 'percent',
            'company_id': self.env.company.id,
        })
        self.line.tax_ids = [(5, 0, 0)]
        self._run(xml)
        self.assertIn(tax0, self.line.tax_ids)

    def test_no_tax_nodes(self):
        xml = """
        <Invoice>
          <cac:Item xmlns="x">
            <!-- No tax nodes -->
          </cac:Item>
        </Invoice>
        """
        self.line.tax_ids = [(5, 0, 0)]
        self._run(xml)
        self.assertFalse(self.line.tax_ids)

    def test_multiple_tax_categories_with_valid_S(self):
        xml = """
        <Invoice>
          <cac:Item xmlns="x">
            <cac:ClassifiedTaxCategory>
              <ID>O</ID><Percent>0</Percent>
            </cac:ClassifiedTaxCategory>
            <cac:ClassifiedTaxCategory>
              <ID>S</ID><Percent>19</Percent>
            </cac:ClassifiedTaxCategory>
          </cac:Item>
        </Invoice>
        """
        tax_s = self.env['account.tax'].create({
            'name': 'TaxS', 'amount': 19.0,
            'type_tax_use': 'purchase', 'amount_type': 'percent',
            'company_id': self.env.company.id,
            'tax_exigibility': 'on_payment',
        })
        self.partner.l10n_ro_vat_on_payment = True
        self.line.tax_ids = [(5, 0, 0)]
        self._run(xml)
        self.assertIn(tax_s, self.line.tax_ids)

    def test_invalid_tax_nodes(self):
        xml = """
        <Invoice>
          <cac:Item xmlns="x">
            <cac:ClassifiedTaxCategory>
              <ID>INVALID</ID><Percent>19</Percent>
            </cac:ClassifiedTaxCategory>
          </cac:Item>
        </Invoice>
        """
        self.line.tax_ids = [(5, 0, 0)]
        self._run(xml)
        self.assertFalse(self.line.tax_ids)

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

    def test_missing_tax_percent(self):
        xml = """
        <Invoice>
          <cac:Item xmlns="x">
            <cac:ClassifiedTaxCategory>
              <ID>S</ID>
              <!-- Missing Percent -->
            </cac:ClassifiedTaxCategory>
          </cac:Item>
        </Invoice>
        """
        self.partner.l10n_ro_vat_on_payment = True
        self.line.tax_ids = [(5, 0, 0)]
        self._run(xml)
        self.assertFalse(self.line.tax_ids)
