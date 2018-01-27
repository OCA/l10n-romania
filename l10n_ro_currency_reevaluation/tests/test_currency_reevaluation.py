# Copyright  2018 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import tools
from odoo.tests.common import TransactionCase
from odoo.modules.module import get_module_resource


class TestCurrencyReevaluation(TransactionCase):
    def _load(self, module, *args):
        tools.convert_file(self.cr, 'l10n_ro_currency_reevaluation',
                           get_module_resource(module, *args),
                           {}, 'init', False, 'test',
                           self.registry._assertion_report)

    def setUp(cls):
        super(TestCurrencyReevaluation, cls).setUp()
        ref = cls.env.ref
        curr_rate_model = cls.env['res.currency.rate']

        # Load minimal account chart
        cls._load('account', 'test', 'account_minimal_test.xml')

        # Set currency EUR on company
        company = ref('base.main_company')
        values = {'currency_id': ref('base.EUR').id,
                  'country_id': ref('base.ro').id}
        company.write(values)

        cls.reval_journal = company.currency_exchange_journal_id
        cls.debit_acc = cls.reval_journal.default_debit_account_id
        cls.credit_acc = cls.reval_journal.default_credit_account_id

        # create rates in USD
        usd_currency = ref('base.USD')
        curr_rate_model.create({
            'rate': 1.5,
            'currency_id': usd_currency.id,
            'name': '2017-01-01'})
        curr_rate_model.create({
            'rate': 1.25,
            'currency_id': usd_currency.id,
            'name': '2017-01-21'})
        curr_rate_model.create({
            'rate': 1.45,
            'currency_id': usd_currency.id,
            'name': '2017-01-31'})

        cls.bank_journal_usd = ref(
            'l10n_ro_currency_reevaluation.bank_journal_usd')
        cls.bank_account_usd = ref('l10n_ro_currency_reevaluation.usd_bnk')

        cls.sequence = cls.env['ir.sequence'].create({
            'name': 'Test account move sequence',
            'padding': 3,
            'prefix': 'sale',
        })
        cls.journal = cls.env['account.journal'].create({
            'name': 'Test Sales Journal - USD',
            'code': 'sale_usd',
            'type': 'sale',
            'sequence_id': cls.sequence.id,
            'update_posted': True,
            'currency_id': usd_currency.id,
            'default_debit_account_id': ref(
                'l10n_ro_currency_reevaluation.a_sale').id,
            'default_credit_account_id': ref(
                'l10n_ro_currency_reevaluation.a_sale').id
        })
        revenue_acc = ref('l10n_ro_currency_reevaluation.a_sale')
        cls.receivable_acc = ref('l10n_ro_currency_reevaluation.a_recv')
        cls.receivable_acc.write({'currency_reevaluation': True})

        invoice_line_data = {
            'product_id': ref('product.product_product_5').id,
            'quantity': 1.0,
            'account_id': revenue_acc.id,
            'name': 'product test 5',
            'price_unit': 100.00,
            'currency_id': usd_currency.id
        }
        partner = ref('base.res_partner_4')

        invoice = cls.env['account.invoice'].create({
            'name': "Customer Invoice",
            'date_invoice': '2017-01-20',
            'currency_id': usd_currency.id,
            'journal_id': cls.journal.id,
            'partner_id': partner.id,
            'account_id': cls.receivable_acc.id,
            'invoice_line_ids': [(0, 0, invoice_line_data)]
        })
        # Validate invoice
        invoice.action_invoice_open()

        payment_method = ref('account.account_payment_method_manual_in')

        # Register partial payment
        payment = cls.env['account.payment'].create({
            'invoice_ids': [(4, invoice.id, 0)],
            'amount': 50,
            'currency_id': usd_currency.id,
            'payment_date': '2017-01-25',
            'communication': 'Invoice partial payment',
            'partner_id': invoice.partner_id.id,
            'partner_type': 'customer',
            'journal_id': cls.bank_journal_usd.id,
            'payment_type': 'inbound',
            'payment_method_id': payment_method.id,
            'payment_difference_handling': 'open',
            'writeoff_account_id': False,
        })
        payment.post()

    def test_currency_revaluation(self):
        precision = self.env.user.company_id.currency_id.decimal_places
        wizard = self.env['l10n.ro.currency.reevaluation']
        data = {'date_reevaluation': '2017-01-31'}
        wiz = wizard.create(data)
        result = wiz.compute_difference()

        # Assert the wizard show the created revaluation lines
        self.assertEqual(result.get('name'), "Created reevaluation moves")

        reval_moves = self.env['account.move'].search(result['domain'])
        reval_move_lines = self.env['account.move.line'].search(
            [('move_id', 'in', reval_moves._ids)])

        # Assert 4 account.move.line were generated.
        self.assertEqual(len(reval_move_lines), 4)

        for reval_line in reval_move_lines:
            if reval_line.account_id.id == self.receivable_acc.id:
                self.assertIsNotNone(reval_line.partner_id)
                self.assertEqual(reval_line.journal_id.id,
                                 self.reval_journal.id)
                self.assertEqual(round(reval_line.debit, precision), 1.15)
                self.assertEqual(round(reval_line.credit, precision), 0.0)
            elif reval_line.account_id.id == self.credit_acc.id:
                self.assertIsNotNone(reval_line.partner_id.id)
                self.assertEqual(reval_line.journal_id.id,
                                 self.reval_journal.id)
                self.assertEqual(round(reval_line.debit, precision), 0)
                self.assertEqual(round(reval_line.credit, precision), 1.15)
            elif reval_line.account_id.id == self.bank_account_usd.id:
                self.assertEqual(reval_line.journal_id.id,
                                 self.bank_journal_usd.id)
                self.assertEqual(round(reval_line.debit, precision), 0.0)
                self.assertEqual(round(reval_line.credit, precision), 5.52)
            elif reval_line.account_id.id == self.debit_acc.id:
                self.assertEqual(reval_line.journal_id.id,
                                 self.bank_journal_usd.id)
                self.assertEqual(round(reval_line.debit, precision), 5.52)
                self.assertEqual(round(reval_line.credit, precision), 0.0)

    def test_defaults(self):
        wizard = self.env['l10n.ro.currency.reevaluation'].create(
            {'date_reevaluation': '2017-01-31'})
        self.assertEqual(wizard.company_id.id,
                         self.env.ref('base.main_company').id)
