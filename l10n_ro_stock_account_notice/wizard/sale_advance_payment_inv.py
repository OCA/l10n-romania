from odoo import api, fields, models, _

class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"
    
    picking_notice = fields.Boolean(string=_("Invoice Picking Notice"))
    picking_notice_count = fields.Integer(compute="_compute_picking_notice")
    picking_notice_ids = fields.Many2many(comodel_name="stock.picking")
    
    def _compute_picking_notice(self):
        models._logger.error(self._context.get('active_ids', []))
        for s in self:
            pikings = s._getUninvoicedPickingOrder()
            s.picking_notice_count = len(pikings)

    def _getUninvoicedPickingOrder(self):
        orders = self.env['sale.order'].browse(self._context.get('active_ids', []))
        return orders.mapped('picking_ids').filtered(lambda x: x.notice and x.invoiced_state!='done')

    @api.onchange('picking_notice')
    def _changePickingNoticeField(self):
        pikings = self._getUninvoicedPickingOrder()
        return {
            'domain':{'picking_notice_ids':[('id','in',pikings.ids)]},
            'value':{
                'picking_notice_count': len(pikings),
                'picking_notice_ids': [(5,)],
                }
            }
        
    def create_invoices(self):
        ctx = self._context.copy()
        ctx.update({
            'picking_ids': self.picking_notice_ids.ids
            })
        return super(SaleAdvancePaymentInv, self.with_context(ctx)).create_invoices()