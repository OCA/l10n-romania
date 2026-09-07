# Romania - Retail Landed Cost (Marfa in Magazin)

Keeps account 371 at the shelf price when a landed cost raises the cost
of goods that are sitting in a retail warehouse.

Goods in a shop are carried at the price on the shelf label. A landed
cost - transport, customs, a purchase price difference - debits 371 with
the extra cost, which for a shop is wrong: the shelf price has not
moved, so the value on 371 must not move either. What changes is how
that value splits: the cost goes up and the markup goes down by the same
amount.

This module posts the compensating entry, `Dr 378 / Cr 371`, and records
it in the markup ledger, so the next sale releases the markup that is
really left rather than the one loaded at reception.

Price differences from vendor bills are handled by the same mechanism:
in this localization a price difference *is* a landed cost, of type
`price_diff`.

If the extra cost would push the markup below zero - the goods now cost
more than they are priced at - the landed cost is refused, naming the
product and the shelf price that would make it work. A shop that
genuinely sells below cost ticks *Allow Selling Below Cost* on the
warehouse, the same flag the reception path honours.
