# ©  2008-2018 Fekete Mihai <mihai.fekete@forbiom.eu>
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details

from odoo import _, api, fields, models

JOURNAL_TYPE_MAP = {
    ("outgoing", "customer"): ["sale"],
    ("outgoing", "supplier"): ["purchase_refund"],
    ("outgoing", "transit"): ["sale", "purchase_refund"],
    ("internal", "in_custody"): ["purchase"],
    ("incoming", "supplier"): ["purchase"],
    ("incoming", "customer"): ["sale_refund"],
    ("incoming", "transit"): ["purchase", "sale_refund"],
}

# frumos in 10 nu mai exita!!!
class stock_invoice_onshipping(models.TransientModel):
    _inherit = "stock.invoice.onshipping"

    def _get_journal_type(self, cr, uid, context=None):
        res = super(stock_invoice_onshipping, self)._get_journal_type(cr, uid, context)
        if context is None:
            context = {}
        res_ids = context and context.get("active_ids", [])
        pick_obj = self.pool.get("stock.picking")
        pickings = pick_obj.browse(cr, uid, res_ids, context=context)
        pick = pickings and pickings[0]
        type = pick.picking_type_id.code
        if (
            type == "internal"
            and pick.move_lines[0].location_id.usage == "in_custody"
            and pick.move_lines[0].location_dest_id.usage == "internal"
        ):
            usage = pick.move_lines[0].location_id.usage
            res = JOURNAL_TYPE_MAP.get((type, usage), ["sale"])[0]
        return res

    _defaults = {
        "journal_type": _get_journal_type,
    }
