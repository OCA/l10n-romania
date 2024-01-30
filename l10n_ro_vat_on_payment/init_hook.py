# Copyright (C) 2023 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


import os
import shutil

from odoo.tools.misc import config, file_path


def pre_init_hook(env):
    data_dir = config["data_dir"]
    istoric_file = os.path.join(data_dir, "istoric.txt")

    test_file = file_path("l10n_ro_vat_on_payment/tests/istoric.txt")
    shutil.copyfile(test_file, istoric_file)
