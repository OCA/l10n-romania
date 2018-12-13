# Copyright  2017 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import datetime

from odoo.tests import common


class TestHRMedicalHolidaysbase(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestHRMedicalHolidaysbase, cls).setUpClass()
        # Configure employees
        cls.employee_root = cls.env.ref('hr.employee_root')
        cls.employee_mit = cls.env.ref('hr.employee_mit')

        # Configure leave statuses
        cls.leave01 = cls.env.ref(
            'l10n_ro_hr_medical_holidays.hr_holidays_status_demo_cm_01')
        cls.leave15 = cls.env.ref(
            'l10n_ro_hr_medical_holidays.hr_holidays_status_demo_cm_15')
        cls.comp = cls.env.ref('hr_holidays.holiday_status_comp')
        cls.newstatus = cls.env['hr.holidays.status'].create(
            {'name': 'Med1',
             'color_name': 'lightcoral',
             'timesheet_generate': False})

        # Configure diseases
        cls.disease1 = cls.env.ref(
            'l10n_ro_hr_medical_holidays.hr_medical_disease_demo_1')
        cls.disease2 = cls.env.ref(
            'l10n_ro_hr_medical_holidays.hr_medical_disease_demo_2')

        # Configure emergency diseases
        cls.edisease1 = cls.env.ref(
            'l10n_ro_hr_medical_holidays.hr_medical_emergency_disease_demo_1')

        # Configure infecto diseases
        cls.idisease1 = cls.env.ref(
            'l10n_ro_hr_medical_holidays.hr_medical_infecto_disease_demo_1')

        # Configure leaves
        cls.initleave = cls.env['hr.holidays'].create(
            {'name': 'Med1',
             'holiday_status_id': cls.leave01.id,
             'date_from': datetime.today().strftime('%Y-%m-01 10:00:00'),
             'date_to': datetime.today().strftime('%Y-%m-04 18:00:00'),
             'type': 'remove',
             'employee_id': cls.employee_mit.id,
             'disease_id': cls.disease1.id})
        cls.leave = cls.env['hr.holidays'].create(
            {'name': 'Med2',
             'holiday_status_id': cls.leave01.id,
             'date_from': datetime.today().strftime('%Y-%m-05 10:00:00'),
             'date_to': datetime.today().strftime('%Y-%m-08 18:00:00'),
             'type': 'remove',
             'employee_id': cls.employee_mit.id,
             'disease_id': cls.disease1.id,
             'initial_id': cls.initleave.id})


class TestHRMedicalHolidays(TestHRMedicalHolidaysbase):
    def test_status_leave_code(self):
        # Test leave status calculation
        self.leave15.indemn_code = '16'
        self.assertEqual(self.leave15.leave_code, 'SL16')
        self.leave15.is_sick_leave = False
        self.assertEqual(self.leave15.leave_code, 'RM')

    def test_status_name_get_search(self):
        # Test leave status calculation
        self.assertEqual(self.leave15.name_get()[0][1], '15 - Risc maternal')
        self.assertEqual(self.comp.name_get()[0][1], 'Compensatory Days')
        leave_id = self.env['hr.holidays.status'].name_search(
            name="15", operator='ilike', args=[])
        self.assertEqual(self.leave15.id, leave_id[0][0])

    def test_disease_name_get_search(self):
        # Test leave status calculation
        self.assertEqual(self.disease1.name_get()[0][1], '1 - Holera')
        disease_id = self.env['hr.medical.disease'].name_search(
            name="1", operator='ilike', args=[])
        self.assertEqual(self.disease1.id, disease_id[0][0])

    def test_edisease_name_get_search(self):
        # Test leave status calculation
        self.assertEqual(self.edisease1.name_get()[0][1], '1 - arsurile')
        disease_id = self.env['hr.medical.emergency.disease'].name_search(
            name="1", operator='ilike', args=[])
        self.assertEqual(self.edisease1.id, disease_id[0][0])

    def test_idisease_name_get_search(self):
        # Test leave status calculation
        self.assertEqual(self.idisease1.name_get()[0][1],
                         '1 - amibiaza (dizenterie amibiana)')
        disease_id = self.env['hr.medical.infecto.disease'].name_search(
            name="1", operator='ilike', args=[])
        self.assertEqual(self.idisease1.id, disease_id[0][0])

    def test_validation_leave_status(self):
        # Test leave status medical warnings
        with self.assertRaises(Exception):
            self.newstatus.write(
                {'is_sick_leave': True,
                 'indemn_code': False})
        with self.assertRaises(Exception):
            self.newstatus.write(
                {'is_sick_leave': True,
                 'indemn_code': '20',
                 'percentage': False})

    def test_initial_medical_leave(self):
        # Test medical leave initial constrains
        with self.assertRaises(Exception):
            self.leave.holiday_status_id = self.leave15.id
        with self.assertRaises(Exception):
            self.leave.disease_id = self.disease2.id
        with self.assertRaises(Exception):
            self.leave.date_from = datetime.today().strftime(
                '%Y-%m-06 10:00:00')

    def test_compute_medical_days(self):
        # Test medical leave days calculation
        self.initleave.employer_days = 4
        self.initleave.budget_days = 0
        self.leave.employer_days = 1
        self.leave.budget_days = 3
