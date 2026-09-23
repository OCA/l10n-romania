Keeps the cash register (registru de casa) of a cash journal.

Every payment posted in a cash journal set to keep a register is added to
the register of its day, which is opened when it does not exist yet.

The payment and its register line are two entries: the payment moves the
money to the account of its payment method (4111 = 581), the line of the
register brings it into the cash account (5311 = 581), and the module
reconciles the two with each other. So the line never has to be
reconciled by hand, and the register shows the cash as it moves.

The module also numbers the documents of a cash journal with sequences of
its own, instead of letting Odoo build the numbers: receipt (chitanta),
cash in and cash out slips (dispozitie de incasare / de plata) and the
register itself.

A sequence can be set on any other journal as well, in *Journal sequence*,
and the entries of that journal are then numbered from it: the invoices of
a sale journal, the bills of a purchase one, the entries of a
miscellaneous one.
