# Copyright (C) 2014 Forest and Biomass Romania
# Copyright (C) 2020 NextERP Romania
# Copyright (C) 2020 Terrabit
# Copyright (C) 2020 Dakai Soft
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models
_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    # Stock Valuation Layer il legam de stock.move.line, pastram referinta la stock.move.
    
    # Mutam generate SVL transfer pe move_line
    def _create_internal_transfer_svl(self, forced_quantity=None):
        svl = self.mapped("move_line_ids")._create_internal_transfer_svl(forced_quantity=forced_quantity)
        #raise
        return svl


    # nu se mai face in mod automat evaluarea la intrare in stoc
    def _create_in_svl(self, forced_quantity=None):
        _logger.debug("SVL:%s" % self.env.context.get("valued_type", ""))
        svl = self.env["stock.valuation.layer"]
        _logger.error([self.env.context, self.env.context.get("standard") or not self.company_id.romanian_accounting, not self.company_id.romanian_accounting])
        if self.env.context.get("standard") or not self.company_id.romanian_accounting:
            svl |= self.mapped("move_line_ids")._create_in_svl(forced_quantity)
        else:
            svl = self.env["stock.valuation.layer"]
        return svl

    # nu se mai face in mod automat evaluarea la iserirea din stoc
    def _create_out_svl(self, forced_quantity=None):
        _logger.debug("SVL:%s" % self.env.context.get("valued_type", ""))
        svl = self.env["stock.valuation.layer"]
        if self.env.context.get("standard") or not self.company_id.romanian_accounting:
            svl |= self.mapped("move_line_ids")._create_out_svl(forced_quantity=forced_quantity)
        else:
            svl = self.env["stock.valuation.layer"]
        return svl


    # Metodele pentru SVL dropshipping raman neschimbate, dropshipping nu influenteaza metoda FIFO
    def _create_dropshipped_svl(self, forced_quantity=None):
        return super(StockMove, self)._create_dropshipped_svl(forced_quantity=forced_quantity)

    def _create_dropshipped_returned_svl(self, forced_quantity=None):
        return super(StockMove, self)._create_dropshipped_returned_svl(forced_quantity=forced_quantity)

