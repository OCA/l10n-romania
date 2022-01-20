import logging as _logging_module
import os

from odoo import tools

logger = _logging_module.getLogger("l10n_ro_payment_receipt_report")
logger.setLevel(_logging_module.DEBUG)


# copy-paste from openupgrade
def load_data(cr, module_name, filename, idref=None, mode="init"):
    """
    Load an xml, csv or yml data file from your post script. The usual case for
    this is the
    occurrence of newly added essential or useful data in the module that is
    marked with "noupdate='1'" and without "forcecreate='1'" so that it will
    not be loaded by the usual upgrade mechanism. Leaving the 'mode' argument
    to its default 'init' will load the data from your migration script.

    Theoretically, you could simply load a stock file from the module, but be
    careful not to reinitialize any data that could have been customized.
    Preferably, select only the newly added items. Copy these to a file
    in your migrations directory and load that file.
    Leave it to the user to actually delete existing resources that are
    marked with 'noupdate' (other named items will be deleted
    automatically).


    :param module_name: the name of the module
    :param filename: the path to the filename, relative to the module \
    directory. This may also be the module directory relative to --upgrade-path
    :param idref: optional hash with ?id mapping cache?
    :param mode:
        one of 'init', 'update', 'demo', 'init_no_create'.
        Always use 'init' for adding new items from files that are marked with
        'noupdate'. Defaults to 'init'.

        'init_no_create' is a hack to load data for records which have
        forcecreate=False set. As those records won't be recreated during the
        update, standard Odoo would recreate the record if it was deleted,
        but this will fail in cases where there are required fields to be
        filled which are not contained in the data file.
    """

    if idref is None:
        idref = {}
    logger.info("%s: loading %s" % (module_name, filename))
    _, ext = os.path.splitext(filename)
    pathname = os.path.join(module_name, filename)

    try:
        fp = tools.file_open(pathname)
    except OSError:
        if tools.config.get("upgrade_path"):
            pathname = os.path.join(tools.config["upgrade_path"], module_name, filename)
            fp = open(pathname)
        else:
            raise

    try:
        # if ext == '.csv':
        #     noupdate = True
        #     tools.convert_csv_import(
        #         cr, module_name, pathname, fp.read(), idref, mode, noupdate)
        # elif ext == '.yml':
        #     yaml_import(cr, module_name, fp, None, idref=idref, mode=mode)
        # elif mode == 'init_no_create':
        #     for fp2 in _get_existing_records(cr, fp, module_name):
        #         tools.convert_xml_import(
        #             cr, module_name, fp2, idref, mode='init',
        #         )
        # else:
        tools.convert_xml_import(cr, module_name, fp, idref, mode=mode)
    finally:
        fp.close()


def uninstall_hook(cr, registry):
    load_data(
        cr, "l10n_ro_payment_receipt_report", "payment_receipt_report_restore.xml"
    )
