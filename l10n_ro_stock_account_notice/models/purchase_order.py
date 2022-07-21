from odoo import models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"
    
    def action_create_invoice(self):
        ctx = self._context.copy()
        picking_notice = self.mapped("picking_ids").filtered(lambda x: x.notice and x.state=='done' and x.invoiced_state !='done')
        if picking_notice:
            ctx.update({'force_invoice_notice': picking_notice.ids})
        return super(PurchaseOrder, self.with_context(ctx)).action_create_invoice()


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"
    
    def _prepare_account_move_line(self, move=False):
        picking_notice_ids = self._context.get('force_invoice_notice', [])
        if picking_notice_ids:
            piking_moves = self.move_ids.filtered(lambda x: x.picking_id.notice)
            pickings = piking_moves.mapped('picking_id.id')
            specific_picking_notice_with_move = [i for i in picking_notice_ids if i in pickings]
            if not any(specific_picking_notice_with_move):
                return None
        res = super(PurchaseOrderLine, self)._prepare_account_move_line(move=move)
        if picking_notice_ids:
            res['move_line_ids'] = [(6, 0, piking_moves.ids)]
        return res