# ©  2008-2020 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details


from odoo import _, api, fields, models


class res_partner(models.Model):
    _inherit = "res.partner"

    mean_transp = fields.Char(string="Mean transport")


class StockLocation(models.Model):
    _inherit = "stock.location"

    user_id = fields.Many2one("res.users", string="Manager")


class StockPicking(models.Model):
    _inherit = "stock.picking"

    origin = fields.Char(states={"done": [("readonly", False)]})
    delegate_id = fields.Many2one("res.partner", string="Delegate")
    mean_transp = fields.Char(string="Mean transport")

    notice = fields.Boolean(
        "Is a notice", states={"done": [("readonly", True)], "cancel": [("readonly", True)]}, default=False
    )

    """
    invoice_state = fields.Selection([("invoiced", "Invoiced"),
                                      ("2binvoiced", "To Be Invoiced"),
                                      ("none", "Not Applicable")
                                      ], string="Invoice Control")
    """

    @api.onchange("delegate_id")
    def on_change_delegate_id(self):
        if self.delegate_id:
            self.mean_transp = self.delegate_id.mean_transp

    # metoda locala sau se poate in 10 are alt nume
    @api.model
    def _get_invoice_vals(self, key, inv_type, journal_id, move):
        res = super(stock_picking, self)._get_invoice_vals(key, inv_type, journal_id, move)
        if inv_type == "out_invoice":
            res["delegate_id"] = move.picking_id.delegate_id.id
            res["mean_transp"] = move.picking_id.mean_transp
        return res

    """

    def action_invoice_create(self,   journal_id=False, group=False, type='out_invoice' ):
        invoices = []

        if type == 'out_invoice':
            context = {}
            for picking in self :
                context = self._context.copy()
                context['default_delegate_id'] = picking.delegate_id.id
                context['default_mean_transp'] = picking.mean_transp
        picking = self.with_context(context)
        invoices = super(stock_picking, picking ).action_invoice_create(journal_id, group, type)

        return invoices
    """

    def do_print_picking(self):
        self.write({"printed": True})
        if self.picking_type_code == "incoming":
            if self.location_dest_id.merchandise_type == "store":
                res = self.env.ref("l10n_ro_stock_picking_report.action_report_reception_sale_price").report_action(
                    self
                )
            else:
                res = self.env.ref("l10n_ro_stock_picking_report.action_report_reception").report_action(self)

        elif self.picking_type_code == "outgoing":
            res = self.env.ref("l10n_ro_stock_picking_report.action_report_delivery").report_action(self)
        else:
            res = self.env.ref("l10n_ro_stock_picking_report.action_report_internal_transfer").report_action(self)
        return res
