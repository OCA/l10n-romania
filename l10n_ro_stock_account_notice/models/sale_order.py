from odoo import models
from datetime import date

class SaleOrder(models.Model):
    _inherit = "sale.order"
    
    def _create_invoices(self, grouped=False, final=False, date=None):
        if self._context.get('picking_ids', None):
            picking_ids = self._context.get('picking_ids', None) 
            self = self.filtered(lambda x: any([i in x.picking_ids.ids for i in picking_ids]))
        return super(SaleOrder, self)._create_invoices(grouped=grouped, final=final, date=date)

    
    def _get_invoiceable_lines(self, final=False):
        lines = super(SaleOrder, self)._get_invoiceable_lines(final=final)
        picking_ids = self._context.get('picking_ids', [])
        if self._context.get('picking_ids', None):
            lineObj = self.env['sale.order.line']
            for line in lines:
                if not any([i in line.move_ids.mapped('picking_id.id') for i in picking_ids]) and not line.is_downpayment:
                    continue
                lineObj |= line
            lines = lineObj
        return lines
    
class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    
    def _prepare_invoice_line(self, **optional_values):
        if self._context.get('picking_ids', None):
            move_ids = self.move_ids.filtered(lambda x: x.picking_id.id in self._context.get('picking_ids'))
            value = move_ids._get_invoice_from_notice_account_move()

            company = self.order_id.company_id or self.env.company
            valuation_amount = company.currency_id._convert(
                abs(value.get('amount')), self.order_id.currency_id, company, date.today()
            )
            
            optional_values.update({
                'price_unit': valuation_amount/abs(value.get('quantity')),
                'quantity': value.get('quantity'),
                'account_id': value.get('account_id').id,
                'move_line_ids': [(6, 0, move_ids.ids)],
                })
        return super(SaleOrderLine, self)._prepare_invoice_line(**optional_values)
        