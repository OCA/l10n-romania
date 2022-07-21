# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# Copyright (C) 2022 Dakai Soft
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    # Prin acest camp se indica daca un produs care e stocabil trece prin
    # contul 408 / 418 la achizitie sau vanzare
    # receptie/ livrare in baza de aviz
    notice = fields.Boolean(
        "Is a notice",
        states={"done": [("readonly", True)], "cancel": [("readonly", True)]},
        default=False,
        help="With this field the reception/delivery is set as a notice. "
        "The generated account move will contain accounts 408/418.",
    )
    
    # Campul indica facturile corelate cu picking_notice.
    invoice_ids = fields.Many2many(
        comodel_name="account.move", string="Invoices", compute="_compute_invoices"
    )
    
    # Campul indica statusul pe un picking_notice,.
    invoiced_state = fields.Selection([
        ('no-invoiced', 'To invoice'),
        ('partial', 'Partial'),
        ('done', 'Invoiced'),
        ], compute="_compute_invoice_state")
    
    def _compute_invoice_state(self):
        for s in self:
            state = 'no-invoiced'
            inv_to = inv_done = 0
            for move in s.move_ids_without_package:
                if s.notice and s.state=='done':
                    inv_to += move.quantity_done
                    # Consideram ca la emitere factura se factureaza integral cantitatea primita/livrata anterior.
                    inv_done += len(move.invoice_line_ids) and move.quantity_done or 0
            if inv_to > 0 and inv_to < inv_done and s.state=='done':
                state = 'partial'
            elif inv_to == inv_done and s.state=='done':
                state = 'done'
            s.invoiced_state = state
    
    def _compute_invoices(self):
        for s in self:
            s.invoice_ids = [(6, 0, s.move_ids_without_package.mapped("invoice_line_ids.move_id").ids)]
    
    def action_view_invoice(self):
        """This function returns an action that display existing invoices
        of given stock pickings.
        It can either be a in a list or in a form view, if there is only
        one invoice to show.
        """
        self.ensure_one()
        form_view_name = "account.view_move_form"
        xmlid = "account.action_move_out_invoice_type"
        action = self.env["ir.actions.act_window"]._for_xml_id(xmlid)
        if len(self.invoice_ids) > 1:
            action["domain"] = "[('id', 'in', %s)]" % self.invoice_ids.ids
        else:
            form_view = self.env.ref(form_view_name)
            action["views"] = [(form_view.id, "form")]
            action["res_id"] = self.invoice_ids.id
        return action