.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

================================
Romania - Account Period Closing
================================

This module allows you to close incomes, expense, vat between two dates.


Installation
============

To install this module, you need to:

* clone the branch 11.0 of the repository https://github.com/OCA/l10n-romania
* add the path to this repository in your configuration (addons-path)
* update the module list
* search for "Romania - Account Period Closing" in your addons
* install the module

Configuration
=============

* Go to Accounting -> Adviser -> Actions -> Account Period Closing,
  create separate templates for Incomes, Expenses, VAT.
* Income and Expenses templates select "121000" account as debit and credit account.
* For VAT template select closing accounts "442600" and "442700" with 
  debit account "442400" and credit account "442300", plus check the
  Close debit and credit accounts option.

Usage
=====

To use this module, you need to be an account adviser and go to:

Accounting -> Adviser -> Actions -> Account Period Closing
* Select the template to close
* Go to Action -> Close Period, choose the dates and click on the "Close" button.

For accounts that can close on different side (eg. 609, 709, 711xxx) accounts,
go to the account and select the Bypass Closing Side Check option.

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/177/11.0

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/OCA/l10n-romania/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smash it by providing detailed and welcomed feedback.

Credits
=======

Images
------

* Odoo Community Association: `Icon <https://odoo-community.org/logo.png>`_.

Contributors
------------

* Fekete Mihai <feketemihai@gmail.com>

Do not contact contributors directly about support or help with technical issues.

Maintainer
----------

.. image:: https://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

To contribute to this module, please visit https://odoo-community.org.
