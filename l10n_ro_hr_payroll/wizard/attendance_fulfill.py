# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2011 Camptocamp SA (http://www.camptocamp.com)
# All Right Reserved
#
# Author : Guewen Baconnier (Camptocamp)
# Author : Vincent Renaville
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################


from openerp.osv import osv, fields
import openerp.tools as tools
import datetime
import calendar
import pytz
import time
from datetime import datetime, timedelta, date
from dateutil.relativedelta import *
import string
import openerp.addons.decimal_precision as dp

class hr_action_reason(osv.osv):
	_inherit = "hr.action.reason"
	_columns = {
		'action_type': fields.selection([('sign_in', 'Sign in'), ('sign_out', 'Sign out'), ('CO', 'Concediu Odihna'), ('CM', 'Concediu Medical')], "Action Type"),
	}
hr_action_reason()


class hr_attendance(osv.osv):
	_inherit = "hr.attendance"
	_columns = {
		'action': fields.selection([('sign_in', 'Sign in'), ('sign_out', 'Sign out'), ('CO', 'Concediu Odihna'), ('CM', 'Concediu Medical')], "Action Type"),
	}
hr_attendance()

def get_number_days_between_dates(date_from, date_to):
    datetime_from = datetime.strptime(date_from, '%Y-%m-%d')
    datetime_to = datetime.strptime(date_to, '%Y-%m-%d')
    difference = datetime_to - datetime_from
    # return result and add a day
    return difference.days + 1


class hr_attendance_fulfill(osv.osv):
	_name = 'hr.attendance.fulfill'
	_description = "Wizard to fill-in attendance for many days"

	_columns = {
		'date_from': fields.date('Date From', required=True),
		'date_to': fields.date('Date To', required=True),
		'department_id': fields.many2many('hr.department', 'attendence_department_rel', 'att_id', 'department_id', 'Departments'),
		'description': fields.char('Description', size=100, required=True),
	}

	def fulfill_attendance(self, cr, uid, ids, context):
		
		def was_on_leave(employee_id, datetime_day, context=None):
			res = False
			day = datetime_day.strftime("%Y-%m-%d")
			holiday_ids = self.pool.get('hr.holidays').search(cr, uid, [('state','=','validate'),('employee_id','=',employee_id),('type','=','remove'),('date_from','<=',day),('date_to','>=',day)])
			if holiday_ids:
				res = self.pool.get('hr.holidays').browse(cr, uid, holiday_ids[0], context=context)
			return res

		timesheet_obj = self.pool.get('hr_timesheet_sheet.sheet')
		attendance_obj = self.pool.get('hr.attendance')
		employee_obj = self.pool.get('hr.employee')
		contract_obj = self.pool.get('hr.contract')

		# get the wizard datas
		wizard = self.browse(cr, uid, ids, context=context)[0]
		
		contract_ids = contract_obj.browse(cr, uid, contract_obj.search(cr, uid,[('date_start','<=', wizard.date_to),'|',('date_end','=',False),('date_end','>=', wizard.date_from)], context=context), context=context)
		for contract in contract_ids:
			if contract.employee_id.active and contract.working_hours and (contract.employee_id.department_id in wizard.department_id):
				employee = contract.employee_id
				user = employee.user_id
				if contract.employee_id.user_id.partner_id.tz:
				    tz = pytz.timezone(contract.employee_id.user_id.partner_id.tz)
				else:
				    tz = pytz.utc			
				department = employee.department_id
				company = employee.company_id
				contract_id = contract.id
				timesheet_id = timesheet_obj.create(cr, uid, {'name': wizard.description, 'user_id': '1', 'department_id': department.id, 'company_id': company.id, 'date_from': wizard.date_from, 'date_to': wizard.date_to, 'state': 'draft','employee_id': employee.id}, context=context)
				timesheet = timesheet_obj.browse(cr, uid, timesheet_id, context=context)
				program_id = contract.working_hours
				holiday_facade = self.pool.get('hr.holidays.public.line')
				holiday_days = holiday_facade.browse(cr, uid, holiday_facade.search(cr, uid, [('date','>=', wizard.date_from), ('date','<=',wizard.date_to)]))
				hol = []
				for h_day in holiday_days:
					year, month, day = (int(x) for x in h_day.date.split('-'))
					start_date = date(year, month, day)
					day = start_date.day
					if int(day) - datetime.strptime(wizard.date_from, '%Y-%m-%d').day >=0:
						hol.append(int(day) - datetime.strptime(wizard.date_from, '%Y-%m-%d').day)
				day1 = datetime.strptime(wizard.date_from, '%Y-%m-%d').day
				if (contract.date_start <= wizard.date_from):
					start = datetime.strptime(wizard.date_from, '%Y-%m-%d').day 
				else:
					start = datetime.strptime(contract.date_start, '%Y-%m-%d').day
				start = start - datetime.strptime(wizard.date_from, '%Y-%m-%d').day
				if (contract.date_end == False) or (contract.date_end >= wizard.date_to):
					nb_of_days = get_number_days_between_dates(wizard.date_from, wizard.date_to)
				else:
					if (contract.date_start <= wizard.date_from):
						nb_of_days = get_number_days_between_dates(wizard.date_from, contract.date_end)
					else:
						nb_of_days = get_number_days_between_dates(contract.date_start, contract.date_end)
				for day in range(start, nb_of_days):
					leave = was_on_leave(employee.id, datetime.strptime(wizard.date_from, '%Y-%m-%d') + timedelta(days=+day), context=context)
					datetime_current = (datetime.strptime(wizard.date_from, '%Y-%m-%d') + timedelta(days=+day)).strftime('%Y-%m-%d')
					date1 = datetime.strptime(wizard.date_from, '%Y-%m-%d') + timedelta(days=+day)
					if leave:
						if leave.is_sick_leave:
						    act = 'CM'
						else:
						    act = 'CO'
						if 'Normal' in program_id.name:
							for att in program_id.attendance_ids:
								if date.weekday(date1) == int(att.dayofweek):
									hour = int(att.hour_from)
									minutes = int(round((att.hour_from - int(att.hour_from)) * 60))
									if hour<10:
										hour1 = '0' + str(hour)
									else:
										hour1 = str(hour)
									if minutes<10:
										minutes1 = '0' + str(minutes)
									else:
										minutes1 = str(minutes)						
									date_start = str(''.join([date1.strftime('%Y-%m-%d'),' ',hour1,':',minutes1,':00']))
									# hh_mm is a tuple (hours, minutes)
									hour = int(att.hour_to)
									minutes = int(round((att.hour_to - int(att.hour_to)) * 60))
									if hour<10:
										hour1 = '0' + str(hour)
									else:
										hour1 = str(hour)
									if minutes<10:
										minutes1 = '0' + str(minutes)
									else:
										minutes1 = str(minutes)						
									date_end = str(''.join([date1.strftime('%Y-%m-%d'),' ',hour1,':',minutes1,':00']))
									att_start = {
										'name': tz.localize(datetime.strptime(date_start,'%Y-%m-%d %H:%M:%S')).astimezone(pytz.utc).strftime('%Y-%m-%d %H:%M:%S'),
										'action': act,
										'employee_id': employee.id,
										'sheet_id': timesheet.id,
									}
									att_end = {
										'name': tz.localize(datetime.strptime(date_end,'%Y-%m-%d %H:%M:%S')).astimezone(pytz.utc).strftime('%Y-%m-%d %H:%M:%S'),
										'action': act,
										'employee_id': employee.id,
										'sheet_id': timesheet.id,
									}
									attendance_obj.create(cr, uid, att_start, context)
									attendance_obj.create(cr, uid, att_end, context)
						else:
							for att in program_id.attendance_ids:
								if (date1.strftime('%Y-%m-%d')[:10] == att.date_from[:10]):
									hour = int(att.hour_from)
									minutes = int(round((att.hour_from - int(att.hour_from)) * 60))
									if hour<10:
										hour1 = '0' + str(hour)
									else:
										hour1 = str(hour)
									if minutes<10:
										minutes1 = '0' + str(minutes)
									else:
										minutes1 = str(minutes)						
									date_start = str(''.join([date1.strftime('%Y-%m-%d'),' ',hour1,':',minutes1,':00']))
									# hh_mm is a tuple (hours, minutes)
									hour = int(att.hour_to)
									minutes = int(round((att.hour_to - int(att.hour_to)) * 60))
									if hour<10:
										hour1 = '0' + str(hour)
									else:
										hour1 = str(hour)
									if minutes<10:
										minutes1 = '0' + str(minutes)
									else:
										minutes1 = str(minutes)						
									date_end = str(''.join([date1.strftime('%Y-%m-%d'),' ',hour1,':',minutes1,':00']))
									att_start = {
										'name': tz.localize(datetime.strptime(date_start,'%Y-%m-%d %H:%M:%S')).astimezone(pytz.utc).strftime('%Y-%m-%d %H:%M:%S'),
										'action': act,
										'employee_id': employee.id,
										'sheet_id': timesheet.id,
									}
									att_end = {
										'name': tz.localize(datetime.strptime(date_end,'%Y-%m-%d %H:%M:%S')).astimezone(pytz.utc).strftime('%Y-%m-%d %H:%M:%S'),
										'action': act,
										'employee_id': employee.id,
										'sheet_id': timesheet.id,
									}
									attendance_obj.create(cr, uid, att_start, context)
									attendance_oj.create(cr, uid, att_end, context)
					else:
						if ('Normal' in program_id.name):
							for att in program_id.attendance_ids:
								if (str(date.weekday(date1)) == att.dayofweek):
									hour = int(att.hour_from)
									minutes = int(round((att.hour_from - int(att.hour_from)) * 60))
									if hour<10:
										hour1 = '0' + str(hour)
									else:
										hour1 = str(hour)
									if minutes<10:
										minutes1 = '0' + str(minutes)
									else:
										minutes1 = str(minutes)						
									date_start = str(''.join([date1.strftime('%Y-%m-%d'),' ',hour1,':',minutes1,':00']))
									# hh_mm is a tuple (hours, minutes)
									hour = int(att.hour_to)
									minutes = int(round((att.hour_to - int(att.hour_to)) * 60))
									if hour<10:
										hour1 = '0' + str(hour)
									else:
										hour1 = str(hour)
									if minutes<10:
										minutes1 = '0' + str(minutes)
									else:
										minutes1 = str(minutes)						
									date_end = str(''.join([date1.strftime('%Y-%m-%d'),' ',hour1,':',minutes1,':00']))
									att_start = {
										'name': tz.localize(datetime.strptime(date_start,'%Y-%m-%d %H:%M:%S')).astimezone(pytz.utc).strftime('%Y-%m-%d %H:%M:%S'),
										'action': 'sign_in',
										'employee_id': employee.id,
										'sheet_id': timesheet.id,
									}
									att_end = {
										'name': tz.localize(datetime.strptime(date_end,'%Y-%m-%d %H:%M:%S')).astimezone(pytz.utc).strftime('%Y-%m-%d %H:%M:%S'),
										'action': 'sign_out',
										'employee_id': employee.id,
										'sheet_id': timesheet.id,
									}
									attendance_obj.create(cr, uid, att_start, context)
									attendance_obj.create(cr, uid, att_end, context)
						else:
							for att in program_id.attendance_ids:
								if (date1.strftime('%Y-%m-%d')[:10] == att.date_from[:10]):
									hour = int(att.hour_from)
									minutes = int(round((att.hour_from - int(att.hour_from)) * 60))
									if hour<10:
										hour1 = '0' + str(hour)
									else:
										hour1 = str(hour)
									if minutes<10:
										minutes1 = '0' + str(minutes)
									else:
										minutes1 = str(minutes)						
									date_start = str(''.join([date1.strftime('%Y-%m-%d'),' ',hour1,':',minutes1,':00']))
									# hh_mm is a tuple (hours, minutes)
									hour = int(att.hour_to)
									minutes = int(round((att.hour_to - int(att.hour_to)) * 60))
									if hour<10:
										hour1 = '0' + str(hour)
									else:
										hour1 = str(hour)
									if minutes<10:
										minutes1 = '0' + str(minutes)
									else:
										minutes1 = str(minutes)						
									date_end = str(''.join([date1.strftime('%Y-%m-%d'),' ',hour1,':',minutes1,':00']))
									att_start = {
										'name': tz.localize(datetime.strptime(date_start,'%Y-%m-%d %H:%M:%S')).astimezone(pytz.utc).strftime('%Y-%m-%d %H:%M:%S'),
										'action': 'sign_in',
										'employee_id': employee.id,
										'sheet_id': timesheet.id,
									}
									att_end = {
										'name': tz.localize(datetime.strptime(date_end,'%Y-%m-%d %H:%M:%S')).astimezone(pytz.utc).strftime('%Y-%m-%d %H:%M:%S'),
										'action': 'sign_out',
										'employee_id': employee.id,
										'sheet_id': timesheet.id,
									}
									attendance_obj.create(cr, uid, att_start, context)
									attendance_obj.create(cr, uid, att_end, context)										
										
		return {'type': 'ir.actions.act_window_close'}
	
hr_attendance_fulfill()
