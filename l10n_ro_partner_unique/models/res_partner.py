# -*- coding: utf-8 -*-
# ©  2015 Forest and Biomass Services Romania
# See README.rst file on addons root folder for license details

from openerp import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _auto_init(self, cr, context=None):
        # Remove vat and nrc unique constraints from Odoo base addons from
        # https://github.com/odoo/odoo/blob/8.0/addons/l10n_ro/res_partner.py
        # history, if exists, and add a new one based on
        # company_id, vat and nrc pair.
        result = super(ResPartner, self)._auto_init(cr, context=context)
        # Real implementation of the vat/nrc constraints: only
        # "commercial entities" need to have unique numbers, and the condition
        # for being a commercial entity is "is_company or parent_id IS NULL".
        # Contacts inside a company automatically have a copy of the company's
        # commercial fields (see _commercial_fields()), so they are
        # automatically consistent.
        cr.execute("""
            DROP INDEX IF EXISTS res_partner_vat_nrc_uniq_for_companies;
            DROP INDEX IF EXISTS res_partner_vat_uniq_for_companies;
            DROP INDEX IF EXISTS res_partner_nrc_uniq_for_companies;
            CREATE UNIQUE INDEX res_partner_vat_nrc_uniq_for_companies
                ON res_partner (company_id, vat, nrc) WHERE is_company OR
                parent_id IS NULL;
        """)
        return result
