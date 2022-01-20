from odoo.tools import convert_file


def uninstall_hook(cr, registry):
    convert_file(
        cr, "l10n_ro_payment_receipt_report", "payment_receipt_report_restore.xml", None
    )
