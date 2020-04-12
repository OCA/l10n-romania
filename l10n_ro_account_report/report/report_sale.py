# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError,ValidationError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class RaportSale(models.TransientModel):
    _name = 'report.l10n_ro_account_report.report_sale'
    _description = 'Report Sale ANAF'

    @api.model    
    def _get_report_values(self,docids,  data=None ):
        date_from = data['form']['date_from']
        date_to = data['form']['date_to']
        company_id = data['form']['company_id']
        invoices = self.env['account.move'].search([
             ('type', 'in',  ['out_invoice', 'out_refund', 'out_receipt'] ), # puchase ['in_invoice', 'in_refund',  'in_receipt']
             ('state','=','posted'),
             ('invoice_date','>=',date_from),('invoice_date','<=',date_to),
             ('company_id','=', company_id[0]),
        ],order='invoice_date, name')
        
        show_warnings = data['form']['show_warnings']
        
        report_type_sale = data['form']['journal']=='sale'
        report_lines,totals = self.compute_report_lines(invoices,data,show_warnings,report_type_sale)
        
        docargs = { 
            'print_datetime':fields.datetime.now(),
            'date_from':date_from,
            'date_to':date_to,
            'show_warnings':show_warnings,
            'user':self.env.user.name,
            'company':self.env['res.company'].browse(company_id[0]),
            'lines':report_lines,
            'totals':totals,
            'report_type_sale':report_type_sale,
        }
        return docargs
    
    def compute_report_lines(self,invoices,data,show_warnings,report_type_sale=True):
        """returns a list of a dictionary for table with the key as column 
        and total dictionary with the sums of columns """
        
        # find all the keys for dictionary  
        #maybe posible_tags must be put manually, but if so, to be the same as account.account.tag name
        posible_tags = self.env['account.account.tag'].search([('country_id','=',self.env.ref('base.ro').id),('applicability','=',"taxes")]).read(['name'])
        posible_tags_just_names = [x['name'] for x in posible_tags]
#         for x in posible_tags_just_names:
#             print(f"'{x}'")

        #future posbile_tags_in_sale & posbile_tags_in_purchase and if something not right  

        #in aggregated_dict the key represent the new key that has as value list of keys that must be summed ( children)
        aggregated_dict = {'total_base':[],'total_vat':[]}  
        aggregated_dict['total_base'] = [x for x in posible_tags_just_names if 
                            ('% (deductibila)' in x) or
                            ('+Baza TVA' in x and '%' == x[-1]) or
                            ('-Baza TVA' in x and '%' == x[-1])   ]
        aggregated_dict['total_vat'] = [x for x in posible_tags if 
                            ('% (TVA colectata)' in x) or
                            ('% (deductibila)' in x and 'TVA' in x)   ]

        report_lines = []
        for inv1 in invoices:
            vals = {x:0 for x in posible_tags_just_names}
            vals['number'] = inv1.name
            vals['date'] = inv1.invoice_date
            vals['partner'] = inv1.invoice_partner_display_name
            vals['vat'] = inv1.partner_stored_vat
            vals['total'] = inv1.amount_total_signed
            vals['warnings'] = ''

            for line in inv1.line_ids:
                if line.account_id.code.startswith('411') or line.account_id.code.startswith('401'):
                    if vals['total'] != -line.credit+line.debit:
                        vals['warnings']+=f"The value of invoice is {vals['total']} but accounting account {line.account_id.code} has a value of  {line.credit-line.debit}"   
                else:
                    if not line.tag_ids or len(line.tag_ids)>1: # or if no tva put tva 0 in future
                        vals['warnings']+=f"line id={line.id} name={line.name}  does not have line_tag_ids or have more and I'm not going to guess it ( maybe in future); "
                    elif line.tag_ids[0].name not in posible_tags_just_names:
                        vals['warnings']+=f"this tag_ids={line.tag_ids[0].name} is not in  find_all_account_tax_report_line"
                    else:
#                        print(f"line.tag_ids[0].name '{line.tag_ids[0].name}' ={line.credit-line.debit}")
                        vals[line.tag_ids[0].name] += line.credit-line.debit

            #put the aggregated values
            for key,value in aggregated_dict.items():
                vals[key] = sum([vals[x] for x in value])
         
            report_lines += [vals]

        #make the totals dictionary for total line of table as sum of all the integer/int values of vals
        int_float_keys = []
        for key,value in report_lines[0].items():
            if (type(value) is int) or (type(value) is float):
                int_float_keys.append(key)
        totals = {}
        for key in int_float_keys:
            totals[key] = sum([x[key] for x in report_lines])
        return report_lines,totals
""" SALE                                          PURCHASE                                             "
"    in report                                             in report                                   "    
    '-Baza TVA 0%'
    '+Baza TVA 0%'
    '-Baza TVA 19%'
    '+Baza TVA 19%'
    '-Baza TVA 24%'
    '+Baza TVA 24%'
    '-Baza TVA 5%'
    '+Baza TVA 5%'
    '-Baza TVA 9%'
    '+Baza TVA 9%'
'-Baza TVA Intracomunitar Bunuri'
'+Baza TVA Intracomunitar Bunuri'
'-Baza TVA Intracomunitar Servicii'
'+Baza TVA Intracomunitar Servicii'
    '-Baza TVA Taxare Inversa'
    '+Baza TVA Taxare Inversa'
'-TVA Taxare Inversa (TVA colectata)'
'+TVA Taxare Inversa (TVA colectata)'
    '-TVA 0% (TVA colectata)'
    '+TVA 0% (TVA colectata)'
    '-TVA 19% (TVA colectata)'
    '+TVA 19% (TVA colectata)'
    '-TVA 24% (TVA colectata)'
    '+TVA 24% (TVA colectata)'
    '-TVA 5% (TVA colectata)'
    '+TVA 5% (TVA colectata)'
    '-TVA 9% (TVA colectata)'
    '+TVA 9% (TVA colectata)'
'-TVA Intracomunitar Bunuri (TVA colectata)'
'+TVA Intracomunitar Bunuri (TVA colectata)'
'-TVA Intracomunitar Servicii (TVA colectata)'
'+TVA Intracomunitar Servicii (TVA colectata)'
                                                '-Baza TVA 0% (deductibila)'
                                                '+Baza TVA 0% (deductibila)'
                                                '-Baza TVA 19% (deductibila)'
                                                '+Baza TVA 19% (deductibila)'
                                                '-Baza TVA 24% (deductibila)'
                                                '+Baza TVA 24% (deductibila)'
                                                '-Baza TVA 5% (deductibila)'
                                                '+Baza TVA 5% (deductibila)'
                                                '-Baza TVA 9% (deductibila)'
                                                '+Baza TVA 9% (deductibila)'
                                                '-Baza TVA Intracomunitar Bunuri (deductibila)'
                                                '+Baza TVA Intracomunitar Bunuri (deductibila)'
                                                '-Baza TVA Intracomunitar Servicii (deductibila)'
                                                '+Baza TVA Intracomunitar Servicii (deductibila)'
                                                '-Baza TVA Taxare Inversa (deductibila)'
                                                '+Baza TVA Taxare Inversa (deductibila)'
'-TVA 0%'
'+TVA 0%'
                                                '-TVA 19% (deductibila)'
                                                '+TVA 19% (deductibila)'
                                                '-TVA 24% (deductibila)'
                                                '+TVA 24% (deductibila)'
                                                '-TVA 5% (deductibila)'
                                                '+TVA 5% (deductibila)'
                                                '-TVA 9% (deductibila)'
                                                '+TVA 9% (deductibila)'
                                                '-TVA Intracomunitar Bunuri (deductibila)'
                                                '+TVA Intracomunitar Bunuri (deductibila)'
                                                '-TVA Intracomunitar Servicii (deductibila)'
                                                '+TVA Intracomunitar Servicii (deductibila)'
                                                '-TVA Taxare Inversa (deductibila)'
                                                '+TVA Taxare Inversa (deductibila)'
'-Baza TVA Taxare Scutita - Achizitii'
'+Baza TVA Taxare Scutita - Achizitii'
                                                '-Baza TVA Taxare Scutita - Vanzari'
                                                '+Baza TVA Taxare Scutita - Vanzari'
    '-Baza TVA Taxare intracomunitara neimpozabila - Achizitii'
    '+Baza TVA Taxare intracomunitara neimpozabila - Achizitii'
                                                '-Baza TVA Taxare intracomunitara neimpozabila - Vanzari'
                                                '+Baza TVA Taxare intracomunitara neimpozabila - Vanzari'
    
    
   """ 