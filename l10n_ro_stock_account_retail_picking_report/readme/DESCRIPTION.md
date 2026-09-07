# Romania - Retail Picking Report (NIR Marfa in Magazin)

Goods entering a shop are received at cost and carried at the shelf
price. The reception note has to show both, and the two accounts that
bridge them, because that is what the person signing it is checking.

This module adds to the valued picking report, for a transfer whose
destination is a retail location:

- purchase unit price and purchase value (the cost)
- markup percentage and markup value (378)
- value excluding VAT, VAT (4428)
- selling price and selling value (the PVA, what 371 carries)

and titles the document *Notă de recepție și constatare de diferențe*
when goods move from a warehouse into a shop.

The figures come from the markup ledger, so the note prints what was
actually loaded on 378 and 4428 for that reception - not a
recomputation from today's pricelist, which would print a different
number every time the shelf price moved.

Installs itself as soon as both the retail accounting and the valued
picking report are present.
