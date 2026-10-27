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

A cash journal which keeps a register needs an **outstanding account** on
its payment methods (*Incoming/Outgoing Payments*), other than the cash
account of the journal. That account is what the register line brings the
money in from:

| entry | debit | credit |
| --- | --- | --- |
| the payment (receipt) | outstanding 581 | receivable 4111 |
| the line of the register | cash 5311 | outstanding 581 |

The module reconciles the two 581 lines with each other, so nothing is
left to match by hand and the line does not show up in the bank
reconciliation screen.

Posting a payment is refused when that account is missing, or when it is
the cash account of the journal itself: the register line would then move
the money from the cash account into the cash account, which is no
movement at all. The message says which account to set.
