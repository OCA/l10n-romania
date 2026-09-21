## The sequence of a journal

*Journal sequence* can be set on any journal, not only on a cash one. The
entries of that journal then take their number from it, instead of from the
numbering Odoo builds itself:

- a sale journal numbers its invoices from it (FCT/00001)
- a purchase journal numbers its bills
- a miscellaneous journal numbers its entries (NC/00001)
- a cash journal numbers the supplier payments and everything which is
  neither a receipt nor a slip, see the table below

The number is taken when the entry is posted: a draft has none yet, and a
draft which is discarded leaves no gap behind. Set *Implementation* to
*No gap* on the sequence if the numbering has to be without holes.

## The cash journal

A cash journal of a romanian company is set up when it is created:

- it is given the sequences of its documents, named after the code of the
  journal:

  | sequence | suffix | numbers |
  | --- | --- | --- |
  | Customer sequence cash in | CH | customer payments (chitanta) |
  | Cash in sequence | DI | money in from a supplier (dispozitie de incasare) |
  | Cash out sequence | DP | money out to a customer (dispozitie de plata) |
  | Statement sequence | RC | the register itself (registru de casa) |
  | Journal sequence | none | supplier payments and the other entries |

- *Romania - Auto Statement* is ticked, which is what makes the journal keep
  a register. Untick it on a journal which should not have one, or create
  the journal with it set to false.

The sequences can be replaced afterwards with sequences of your own; the
module only fills in the ones which are empty.

## The account of the payment method

What the register line looks like depends on the account set on the payment
method of the journal (*Incoming/Outgoing Payments*):

| account | entries | register line |
| --- | --- | --- |
| the cash account of the journal | one | the entry of the payment itself |
| an outstanding (transit) account | two | its own entry, reconciled with the payment |
| none | none | none, there is nothing to register |

The first one is the usual setup of a romanian cash journal: a receipt is
booked straight as 5311 = 4111 and the register shows that entry.

The second one is for the money reaching the cash register through a
transit account (4111 = 581 when the payment is posted, 5311 = 581 in the
register). Both entries are needed here, and the module reconciles them, so
there is still nothing left to do by hand.

The third one only happens in Odoo Enterprise, where a payment method
without an account produces no journal entry at all. Such a payment cannot
be put in a register, and none is created for it.
