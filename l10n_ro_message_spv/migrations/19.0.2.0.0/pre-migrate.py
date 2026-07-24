# Copyright (C) 2026 Dorin Hongu <dhongu(@)gmail(.)com
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import SUPERUSER_ID, api
from odoo.tools.sql import column_exists

_logger = logging.getLogger(__name__)

BATCH_SIZE_PARAM = "l10n_ro_message_spv.migration_batch_size"
DEFAULT_BATCH_SIZE = 1000


def migrate(cr, version):
    """The XML / ANAF PDF / embedded PDF attachments are no longer stored
    per message — they are derived on demand from the signed ZIP. Clean up
    the historical duplicates before the fields become computed:

    - messages linked to an invoice: make sure the derived files live on
      the invoice (the legacy flow already moved most of them there);
    - messages without an invoice: delete the derived files — they can be
      re-extracted from the ZIP at any time.
    """
    # On databases that never stored these fields as plain columns there is
    # nothing to clean up; skip so the migration stays idempotent.
    if not column_exists(cr, "l10n_ro_message_spv", "attachment_xml_id"):
        return

    # Relink derived attachments to the invoice for messages that have one,
    # so the computed fields keep finding them.
    cr.execute(
        """
        UPDATE ir_attachment a
        SET res_model = 'account.move', res_id = m.invoice_id
        FROM l10n_ro_message_spv m
        WHERE m.invoice_id IS NOT NULL
          AND a.id IN (m.attachment_xml_id, m.attachment_anaf_pdf_id,
                       m.attachment_embedded_pdf_id)
          AND (a.res_model IS DISTINCT FROM 'account.move'
               OR a.res_id IS DISTINCT FROM m.invoice_id)
        """
    )
    _logger.info("Relinked %s derived attachments to their invoice", cr.rowcount)

    # Delete the derived attachments of messages without an invoice. Use the
    # ORM so the filestore files are garbage-collected as well — this is
    # where the disk space is actually reclaimed.
    cr.execute(
        """
        SELECT att.id
        FROM l10n_ro_message_spv m
        JOIN ir_attachment att
          ON att.id IN (m.attachment_xml_id, m.attachment_anaf_pdf_id,
                        m.attachment_embedded_pdf_id)
        WHERE m.invoice_id IS NULL
        """
    )
    attachment_ids = [row[0] for row in cr.fetchall()]
    env = api.Environment(cr, SUPERUSER_ID, {})
    get_param = env["ir.config_parameter"].sudo().get_param
    BATCH_SIZE = int(get_param(BATCH_SIZE_PARAM, DEFAULT_BATCH_SIZE))
    for start in range(0, len(attachment_ids), BATCH_SIZE):
        batch = attachment_ids[start : start + BATCH_SIZE]
        env["ir.attachment"].browse(batch).exists().unlink()
    _logger.info(
        "Deleted %s derived attachments of messages without invoice",
        len(attachment_ids),
    )

    # Drop the legacy columns — the fields are computed, non-stored now.
    cr.execute(
        """
        ALTER TABLE l10n_ro_message_spv
        DROP COLUMN IF EXISTS attachment_xml_id,
        DROP COLUMN IF EXISTS attachment_anaf_pdf_id,
        DROP COLUMN IF EXISTS attachment_embedded_pdf_id
        """
    )
