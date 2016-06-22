# -*- coding: utf-8 -*-
# ©  2015 Forest and Biomass Services Romania
# See README.rst file on addons root folder for license details

import os
from datetime import datetime, date
from subprocess import Popen, PIPE

from zipfile import ZipFile
from StringIO import StringIO
import requests

from openerp import models, fields, api, tools
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT

ANAF_URL = 'http://static.anaf.ro/static/10/Anaf/TVA_incasare/ultim_%s.zip'


class ResPartnerAnaf(models.Model):
    _name = "res.partner.anaf"
    _description = "ANAF History about VAT on Payment"
    _order = "vat, operation_date DESC, end_date, start_date"

    anaf_id = fields.Char('ANAF ID', select=True)
    vat = fields.Char('VAT', select=True)
    start_date = fields.Date('Start Date', select=True)
    end_date = fields.Date('End Date', select=True)
    publish_date = fields.Date('Publish Date')
    operation_date = fields.Date('Operation Date')
    operation_type = fields.Selection([('I', 'Register'),
                                       ('E', 'Fix error'),
                                       ('D', 'Removal')],
                                      'Operation Type')

    @api.model
    def download_anaf_data(self):
        """ Download VAT on Payment data from ANAF if the file
            was not modified in the same date
        """
        data_dir = tools.config['data_dir']
        istoric = os.path.join(data_dir, "istoric.txt")
        if os.path.exists(istoric):
            modify = date.fromtimestamp(os.path.getmtime(istoric))
        else:
            modify = date.fromtimestamp(0)
        if bool(date.today() - modify):
            result = requests.get(ANAF_URL % date.today().strftime('%Y%m%d'))
            if result.status_code == requests.codes.ok:
                files = ZipFile(StringIO(result.content))
                files.extractall(path=str(data_dir))

    @api.model
    def _download_anaf_data(self):
        self.download_anaf_data()


class ResPartner(models.Model):
    _name = "res.partner"
    _inherit = "res.partner"

    @api.one
    @api.depends('vat')
    def _compute_vat(self):
        # TO DO: use base_vat split method
        self.vat_number = self.vat and self.vat[2:].replace(' ', '')

    @api.one
    @api.depends('vat_number')
    def _compute_anaf_history(self):
        history = self.env['res.partner.anaf'].search(
            [('vat', '=', self.vat_number)])
        if history:
            self.anaf_history = [(6, 0, [line.id for line in history])]

    vat_on_payment = fields.Boolean('VAT on Payment')
    vat_number = fields.Char(
        'VAT number', compute='_compute_vat',
        help='VAT number without country code.')
    anaf_history = fields.One2many(
        'res.partner.anaf',
        compute='_compute_anaf_history',
        string='ANAF History',
        readonly=True
    )

    @api.model
    def _insert_relevant_anaf_data(self):
        """ Load VAT on payment lines for specified partners."""
        def format_date(date):
            if date != '':
                return datetime.strptime(str(date),
                                         '%Y%m%d').strftime(DATE_FORMAT)
            else:
                return False
        vat_numbers = [
            p.vat_number for p in self if p.vat and p.vat.lower().startswith(
                'ro')
            ]
        if vat_numbers == []:
            return
        anaf_obj = self.env['res.partner.anaf']
        data_dir = tools.config['data_dir']
        istoric = os.path.join(data_dir, "istoric.txt")
        vat_regex = '^[0-9]+#(%s)#' % '|'.join(vat_numbers)
        anaf_data = Popen(['egrep', vat_regex, istoric], stdout=PIPE)
        (process_lines, err) = anaf_data.communicate()
        process_lines = [x.split('#') for x in process_lines.split()]
        lines = self.env['res.partner.anaf'].search([
            ('anaf_id', 'in', [int(x[0]) for x in process_lines])])
        line_ids = [int(l.anaf_id) for l in lines]
        for line in process_lines:
            if int(line[0]) not in line_ids:
                anaf_obj.create({
                    'anaf_id': line[0],
                    'vat': line[1],
                    'start_date': format_date(line[2]),
                    'end_date': format_date(line[3]),
                    'publish_date': format_date(line[4]),
                    'operation_date': format_date(line[5]),
                    'operation_type': line[6]
                })

    @api.multi
    def _check_vat_on_payment(self):
        ctx = dict(self._context)
        vat_on_payment = False
        self._insert_relevant_anaf_data()
        self._compute_anaf_history()
        if self.anaf_history:
            if len(self.anaf_history) > 1 and ctx.get('check_date', False):
                lines = self.env['res.partner.anaf'].search([
                    ('id', 'in', [rec.id for rec in self.anaf_history]),
                    ('start_date', '<=', ctx['check_date']),
                    ('end_date', '>=', ctx['check_date'])
                ])
                if lines and lines[0].operation_type == 'D':
                    vat_on_payment = True
            else:
                if self.anaf_history[0].operation_type == 'I':
                    vat_on_payment = True
        return vat_on_payment

    @api.one
    def check_vat_on_payment(self):
        ctx = dict(self._context)
        ctx.update({'check_date': date.today()})
        self.vat_on_payment = self.with_context(ctx)._check_vat_on_payment()

    @api.multi
    def update_vat_payment_all(self):
        self.env['res.partner.anaf']._download_anaf_data()
        partners = self.search([('vat', '!=', False)])
        partners.check_vat_on_payment()

    @api.model
    def _update_vat_payment_all(self):
        self.update_vat_payment_all()
