# Copyright (C) 2014 Adrian Vasile
# Copyright (C) 2017 FOREST AND BIOMASS ROMANIA SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HRHolidaysStatus(models.Model):
    _inherit = 'hr.holidays.status'

    _sql_constrains = [(
        'sick_leave_uniq',
        'unique (is_sick_leave, emergency, indemn_code)',
        'Only one Indemnization Code/Emergency pair',
    )]

    @api.multi
    @api.depends('name', 'is_sick_leave', 'indemn_code')
    def _compute_leave_code(self):
        for leave in self:
            if leave.is_sick_leave is True:
                leave.leave_code = 'SL' + leave.indemn_code
            else:
                leave.leave_code = \
                    ''.join(x[0] for x in leave.name.split()).upper()

    @api.onchange('is_sick_leave')
    @api.constrains('indemn_code', 'percentage', 'employer_days', 'max_days')
    def _require_values(self):
        for leave in self:
            if leave.is_sick_leave is True:
                if not leave.indemn_code:
                    raise ValidationError(_('Set Indemnization Code'))
                if not leave.percentage:
                    raise ValidationError(_('Set Percentage'))

    @api.multi
    def name_get(self):
        res = []
        for leave in self:
            if leave.indemn_code:
                res.append((leave.id,
                            _("%s - %s") % (leave.indemn_code, leave.name)))
            else:
                res.append((leave.id, _("%s") % (leave.name)))
        return res

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if operator not in ('ilike', 'like', '=', '=like', '=ilike'):
            return super(HRHolidaysStatus, self).name_search(
                name, args, operator, limit)
        args = args or []
        domain = ['|', ('indemn_code', operator, name),
                  ('name', operator, name)]
        recs = self.search(domain + args, limit=limit)
        return recs.name_get()

    leave_code = fields.Char(
        'Leave Code', compute='_compute_leave_code', store=True)
    is_sick_leave = fields.Boolean('Is Sick Leave')
    is_unpaid = fields.Boolean('Is Unpaid')
    emergency = fields.Boolean('Medical Emergency')
    indemn_code = fields.Char('Indemnization Code')
    percentage = fields.Integer('Percentage', default=0)
    employer_days = fields.Integer('# Days by Employer', default=0)
    max_days = fields.Integer('Max # of days', default=0)
    ceiling = fields.Integer('Ceiling', help='Expressed in months', default=0)
    ceiling_type = fields.Selection(
        [('min', 'Minimum Wage'), ('med', 'Medium Wage')],
        string='Ceiling based on')


class HRMedicalDisease(models.Model):
    _name = 'hr.medical.disease'
    _description = "Medical Disease"

    @api.multi
    def name_get(self):
        res = []
        for disease in self:
            res.append((disease.id,
                        _("%s - %s") % (disease.code, disease.name)))
        return res

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if operator not in ('ilike', 'like', '=', '=like', '=ilike'):
            return super(HRMedicalDisease, self).name_search(
                name, args, operator, limit)
        args = args or []
        domain = ['|', ('code', operator, name), ('name', operator, name)]
        recs = self.search(domain + args, limit=limit)
        return recs.name_get()

    code = fields.Char('Code', required=True)
    name = fields.Char('Name', required=True)


class HRMedicalEmergencyDisease(models.Model):
    _name = 'hr.medical.emergency.disease'
    _description = "Medical Emergency Disease"

    @api.multi
    def name_get(self):
        res = []
        for disease in self:
            res.append((disease.id,
                        _("%s - %s") % (disease.code, disease.name)))
        return res

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if operator not in ('ilike', 'like', '=', '=like', '=ilike'):
            return super(HRMedicalEmergencyDisease, self).name_search(
                name, args, operator, limit)
        args = args or []
        domain = ['|', ('code', operator, name), ('name', operator, name)]
        recs = self.search(domain + args, limit=limit)
        return recs.name_get()

    code = fields.Char('Code', required=True)
    name = fields.Char('Name', required=True)


class HRMedicalInfectoDisease(models.Model):
    _name = 'hr.medical.infecto.disease'
    _description = "Medical Infecto Disease"

    @api.multi
    def name_get(self):
        res = []
        for disease in self:
            res.append((disease.id,
                        _("%s - %s") % (disease.code, disease.name)))
        return res

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if operator not in ('ilike', 'like', '=', '=like', '=ilike'):
            return super(HRMedicalInfectoDisease, self).name_search(
                name, args, operator, limit)
        args = args or []
        domain = ['|', ('code', operator, name), ('name', operator, name)]
        recs = self.search(domain + args, limit=limit)
        return recs.name_get()

    code = fields.Char('Code', required=True)
    name = fields.Char('Name', required=True)


class HRHolidays(models.Model):
    _inherit = 'hr.holidays'

    @api.constrains('holiday_status_id', 'initial_id',
                    'disease_id', 'date_from')
    def _validate_sl(self):
        for holiday in self:
            if holiday.initial_id:
                init = holiday.initial_id
                date_from = fields.Datetime.from_string(holiday.date_from)
                date_to = fields.Datetime.from_string(init.date_to)
                if relativedelta(date_from, date_to).days != 0:
                    raise ValidationError(
                        _("Medical Leave date from must be consequent to "
                          "Initial medical leave date to."))
                if holiday.holiday_status_id.id != init.holiday_status_id.id:
                    raise ValidationError(
                        _("Medical Leave must have the same leave type as "
                          "the Initial medical leave."))
                if holiday.disease_id.id != init.disease_id.id:
                    raise ValidationError(
                        _("Medical Leave must have the same disease as the "
                          "Initial medical leave."))

    @api.multi
    @api.depends('date_from', 'date_to', 'holiday_status_id')
    def _compute_holiday_medical_days(self):
        for holiday in self:
            emp_days = 0
            if holiday.is_sick_leave:
                if holiday.initial_id:
                    emp_days += holiday.initial_id.number_of_days_temp
                if emp_days <= holiday.holiday_status_id.employer_days:
                    emp_days = holiday.holiday_status_id.employer_days - \
                        emp_days
                else:
                    emp_days = 0
                if holiday.number_of_days_temp <= emp_days:
                    emp_days = holiday.number_of_days_temp
                holiday.employer_days = emp_days
                holiday.budget_days = holiday.number_of_days_temp - emp_days

    @api.model
    def _get_medical_issuer(self):
        issuer = [('1', 'Medic de familie'),
                  ('2', 'Spital'),
                  ('3', 'Ambulatoriu'),
                  ('4', 'CAS')]
        return issuer

    is_sick_leave = fields.Boolean(
        related='holiday_status_id.is_sick_leave',
        readonly=True, store=True)
    is_unpaid = fields.Boolean(
        related='holiday_status_id.is_unpaid',
        readonly=True, store=True)
    allowance_code = fields.Char(
        'Allowance Code', related='holiday_status_id.indemn_code',
        readonly=True, store=True)
    medical_emergency = fields.Boolean(
        'Medical Emergency', related='holiday_status_id.emergency',
        readonly=True, store=True)
    date_issue = fields.Date('Issue Date', copy=False)
    medleave_issuer = fields.Selection(
        '_get_medical_issuer', string='Medical Leave Issuer', copy=False,
        help="Medical Leave Issuer", default="1")
    medleave_serie = fields.Char('Serie', copy=False)
    medleave_number = fields.Char('Number', copy=False)
    disease_id = fields.Many2one('hr.medical.disease', 'Disease', copy=False)
    infecto_disease_id = fields.Many2one(
        'hr.medical.infecto.disease', 'Infectious-contagious Code',
        copy=False)
    emergency_disease_id = fields.Many2one(
        'hr.medical.emergency.disease', 'Emergecy Code', copy=False)
    expert_number = fields.Char(
        'Expert Number', copy=False,
        help='Number of expert medical opinion')
    date_health = fields.Date(
        'Public Health Direction Date', copy=False,
        help='The date announced at the public health directorate')
    initial_id = fields.Many2one(
        'hr.holidays', 'Initial Sick Leave', copy=False)
    employer_days = fields.Integer(
        '# Days by Employer', compute='_compute_holiday_medical_days',
        store=True)
    budget_days = fields.Integer(
        '# Days by Social Security', compute='_compute_holiday_medical_days',
        store=True)
