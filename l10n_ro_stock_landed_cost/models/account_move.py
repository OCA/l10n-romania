from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    def button_create_landed_costs(self):
        res = super().button_create_landed_costs()
        landed_cost = self.env["stock.landed.cost"].browse(res.get("res_id"))
        if self.company_id.l10n_ro_accounting and landed_cost:
            # if the landed cost is on same invoice as received products
            # will put in landed cost the pickings for this products
            picking_invoice_ids = (
                self.line_ids.mapped("purchase_line_id")
                .mapped("order_id")
                .mapped("picking_ids")
            )
            landed_cost.picking_ids = picking_invoice_ids

            # before the logic was to put only to that pickings that do not have a
            #        landed cost.
            # but is wrong becuase the landed cost is not only the transport
            # picking_landed_cost_ids = self.env['stock.landed.cost'].search(
            #             [('state', '=', 'done')]).mapped('picking_ids')
            # landed_cost.picking_ids = picking_invoice_ids.filtered(lambda l:
            #        l not in picking_landed_cost_ids and l.state == 'done')

            # put the right expense account for romanian accounting
            for line in landed_cost.cost_lines:
                # the line.account_id was stock_input and must be expense
                invoice_line = self.line_ids.filtered(
                    lambda l: l.product_id == line.product_id
                )
                if invoice_line:
                    line.account_id = invoice_line[0].account_id
        return res


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.onchange("is_landed_costs_line")
    def _onchange_is_landed_costs_line(self):
        res = super()._onchange_is_landed_costs_line()
        # romania stock_account localisation is made with anglo_saxon_accounting in
        # company we must change de accounts to be expense and not stock_input
        if (
            self.move_id.company_id.l10n_ro_accounting
            and self.product_type == "service"
            and self.is_landed_costs_line
        ):
            accounts = self.product_id.product_tmpl_id._get_product_accounts()
            self.account_id = accounts["expense"]
        return res
