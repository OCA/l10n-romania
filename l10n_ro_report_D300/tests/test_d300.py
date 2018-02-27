# Copyright  2018 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import time
from odoo.tests.common import TransactionCase


class TestD300Report(TransactionCase):

    def setUp(self):
        super(TestD300Report, self).setUp()
        self.date_from = time.strftime('%Y-%m-01'),
        self.date_to = time.strftime('%Y-%m-28'),
        self.invoice_2 = self.env.ref(
            'l10n_ro_report_D300.demo_invoice_2')
        self.tag_ro_090 = self.env.ref(
            'l10n_ro_report_D300.demo_tax_tag_ro_090')
        self.tag_ro_100 = self.env.ref(
            'l10n_ro_report_D300.demo_tax_tag_ro_100')
        self.tag_ro_110 = self.env.ref(
            'l10n_ro_report_D300.demo_tax_tag_ro_110')
        self.tag_ro_170 = self.env.ref(
            'l10n_ro_report_D300.demo_tax_tag_ro_170')
        self.tax_ro_05 = self.env.ref(
            'l10n_ro_report_D300.demo_tvac_05')
        self.tax_ro_05_cb = self.env.ref(
            'l10n_ro_report_D300.demo_tvaic_05')
        self.bank_journal = self.env['account.journal'].search(
            [('type', '=', 'bank')], limit=1)

    def _get_report_lines(self):
        company = self.env.ref('base.main_company')
        self.invoice_2.pay_and_reconcile(
            self.bank_journal.id, 66.5, time.strftime('%Y-%m-10'))
        d300_report = self.env['l10n_ro_report_d300'].create({
            'date_from': self.date_from,
            'date_to': self.date_to,
            'company_id': company.id,
            'tax_detail': True,
            })
        d300_report.compute_data_for_report()
        lines = {}
        d300_taxtag_model = self.env['l10n_ro_report_d300_taxtag']
        lines['tag_ro_090'] = d300_taxtag_model.search([
            ('report_id', '=', d300_report.id),
            ('taxtag_id', '=', self.tag_ro_090.id),
        ])
        lines['tag_ro_100'] = d300_taxtag_model.search([
            ('report_id', '=', d300_report.id),
            ('taxtag_id', '=', self.tag_ro_100.id),
        ])
        lines['tag_ro_110'] = d300_taxtag_model.search([
            ('report_id', '=', d300_report.id),
            ('taxtag_id', '=', self.tag_ro_110.id),
        ])
        lines['tag_ro_170'] = d300_taxtag_model.search([
            ('report_id', '=', d300_report.id),
            ('taxtag_id', '=', self.tag_ro_170.id),
        ])
        d300_tax_model = self.env['l10n_ro_report_d300_tax']
        lines['tax_05'] = d300_tax_model.search([
            ('report_tax_id', '=', lines['tag_ro_170'].id),
            ('tax_id', '=', self.tax_ro_05.id),
        ])
        lines['tax_05_cb'] = d300_tax_model.search([
            ('report_tax_id', '=', lines['tag_ro_170'].id),
            ('tax_id', '=', self.tax_ro_05_cb.id),
        ])
        lines['tag_ro_170_moves'] = lines['tag_ro_170'].move_line_ids
        lines['tax_ro_05_moves'] = lines['tax_05'].move_line_ids
        return lines

    def test_01_compute(self):
        # Generate the d 300 line
        lines = self._get_report_lines()
        self.assertEqual(len(lines['tag_ro_090']), 1)
        self.assertEqual(len(lines['tag_ro_100']), 1)
        self.assertEqual(len(lines['tag_ro_110']), 1)
        self.assertEqual(len(lines['tag_ro_170']), 1)
        self.assertEqual(len(lines['tax_05']), 1)
        self.assertEqual(len(lines['tax_05_cb']), 1)
        self.assertEqual(len(lines['tag_ro_170_moves']), 6)
        self.assertEqual(len(lines['tax_ro_05_moves']), 1)

        # Check net and tax amounts
        self.assertEqual(lines['tag_ro_090'].net, 150)
        self.assertEqual(lines['tag_ro_090'].tax, 28.5)
        self.assertEqual(lines['tag_ro_100'].net, 150)
        self.assertEqual(lines['tag_ro_100'].tax, 13.5)
        self.assertEqual(lines['tag_ro_110'].net, 150)
        self.assertEqual(lines['tag_ro_110'].tax, 7.5)
        self.assertEqual(lines['tag_ro_170'].net, 450)
        self.assertEqual(lines['tag_ro_170'].tax, 49.5)
        self.assertEqual(lines['tax_05'].net, 100)
        self.assertEqual(lines['tax_05'].tax, 5)
        self.assertEqual(lines['tax_05_cb'].net, 50)
        self.assertEqual(lines['tax_05_cb'].tax, 2.5)

    def test_get_report_html(self):
        company = self.env.ref('base.main_company')
        d300_report = self.env['l10n_ro_report_d300'].create({
            'date_from': self.date_from,
            'date_to': self.date_to,
            'company_id': company.id,
            'tax_detail': True,
            })
        d300_report.compute_data_for_report()
        d300_report.get_html(given_context={})

    def test_wizard_date_range(self):
        d300_wizard = self.env['wizard.l10n.ro.report.d300']
        date_range = self.env['date.range']
        self.type = self.env['date.range.type'].create(
            {'name': 'Month',
             'company_id': False,
             'allow_overlap': False})
        dt = date_range.create({
            'name': 'FS2016',
            'date_start': time.strftime('%Y-%m-01'),
            'date_end': time.strftime('%Y-%m-28'),
            'type_id': self.type.id,
        })
        wizard = d300_wizard.create(
            {'date_range_id': dt.id,
             'date_from': time.strftime('%Y-%m-28'),
             'date_to': time.strftime('%Y-%m-01'),
             'tax_detail': True})
        wizard.onchange_date_range_id()
        self.assertEqual(wizard.date_from, time.strftime('%Y-%m-01'))
        self.assertEqual(wizard.date_to, time.strftime('%Y-%m-28'))
        wizard._export('qweb-pdf')
        wizard.button_export_html()
        wizard.button_export_pdf()
        wizard.button_export_xlsx()
