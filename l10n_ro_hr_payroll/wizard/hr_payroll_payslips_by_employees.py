# Copyright (C) 2020 OdooERP România S.R.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models, _
from odoo.exceptions import UserError


class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    @api.multi
    def compute_sheet(self):
        payslips = self.env['hr.payslip']
        [data] = self.read()
        active_id = self.env.context.get('active_id')
        if active_id:
            [run_data] = \
                self.env['hr.payslip.run'].browse(active_id).read(
                    ['date_start', 'date_end', 'credit_note']
                )
        from_date = run_data.get('date_start')
        to_date = run_data.get('date_end')
        if not data['employee_ids']:
            raise UserError(_(
                "You must select employee(s) to generate payslip(s)."
            ))
        for employee in self.env['hr.employee'].browse(data['employee_ids']):

            contracts = self.env['hr.payslip'].get_contract(
                employee, from_date, to_date
            )
            for contract in self.env['hr.contract'].browse(contracts):
                contract_from_date = from_date
                contract_to_date = to_date
                contract_end_day = False
                if contract.date_end:
                    contract_end_day = contract.date_end
                if contract.date_start > from_date:
                    contract_from_date = contract.date_start
                if contract_end_day and contract_end_day < to_date:
                    contract_to_date = contract_end_day

                slip_data = self.env['hr.payslip'].onchange_employee_id(
                    contract_from_date, contract_to_date,
                    employee.id, contract_id=False
                )
                res = {
                    'employee_id': employee.id,
                    'name': slip_data['value'].get('name'),
                    'struct_id': slip_data['value'].get('struct_id'),
                    'contract_id': contract.id,
                    'payslip_run_id': active_id,
                    'input_line_ids': [
                        (0, 0, x) for x in
                        slip_data['value'].get('input_line_ids')
                    ],
                    'worked_days_line_ids': [
                        (0, 0, x) for x in
                        slip_data['value'].get('worked_days_line_ids')
                    ],
                    'date_from': contract_from_date,
                    'date_to': contract_to_date,
                    'credit_note': run_data.get('credit_note'),
                    'company_id': employee.company_id.id,
                }
                payslips += self.env['hr.payslip'].create(res)
        payslips.compute_sheet()
        return {'type': 'ir.actions.act_window_close'}
