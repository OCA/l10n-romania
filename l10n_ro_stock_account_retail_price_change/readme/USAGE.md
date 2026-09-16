## Changing a shelf price

The shop can start from either end.

**From the document.** *Inventory → Retail → Price Changes*, create one,
pick the warehouse, *Load Products*. Every product on hand in the shop's
retail locations comes in with what it currently carries on the left —
cost, markup and deferred VAT per unit, read from the markup ledger, not
from the price list — and the current shelf price on the right. Edit the
*New PVA* of the lines that are changing, delete the rest, then *Post*.

**From the price list.** Change the price of a product on a shop's
retail pricelist, and a draft Proces Verbal is raised for each retail
warehouse that has that product on hand. It is a draft on purpose:
somebody reviews it and posts it. Deleting a rule raises one too, because
the label changes then as well.

Posting does four things, in one transaction: writes the new prices on
the retail pricelist, posts the revaluation of 371 against 378 and 4428,
records it in the markup ledger so the next sale releases the new markup,
and prints as the *Proces-verbal privind modificarea pretului de vanzare
cu amanuntul*.

The old side and the quantity are re-read at the moment of posting, not
at the moment of loading. A draft raised this morning and posted this
afternoon measures itself against what the shop holds this afternoon, so
two documents on the same goods cannot each revalue from the same
starting point.

## Correcting a document

There is no reset to draft, and a posted document cannot be cancelled or
deleted. It wrote prices, posted an entry and moved what the stock
carries; the paper trail is the point. A price decision that turned out
wrong is revoked the way it was made — post another Proces Verbal
bringing the price back. Only a document still in draft can be cancelled
or deleted.

## Price history

*Price History* on a product lists every posted line that concerns it,
oldest first: the date, the shop, the old and new PVA and the document
that decided each. That is the shelf price history the shop has to be
able to show.

## What raises a document

A Proces Verbal is raised for every shelf price that moves, whatever
decided it. What is compared is the price before and the price after, per
product and per shop, so a rule that names a whole range produces a
document holding the labels that actually changed — not the range.

Caught as it happens, from a write on the price list:

- a fixed price on a product or a template;
- a rule on a **category**, or a **global** rule;
- any term of a **formula** — the base it starts from, the discount or
  markup, the rounding, the extra fee, the margins;
- a change on **another price list the shop derives from**, however long
  the chain: the buyer moves a price on the buying list and the shop's
  labels move with it;
- deleting a rule, because the label changes then as well;
- a change to the product's **sale price**, for the shops that price
  their shelves off it — which is the default setup.

Caught overnight, by *Retail: Reconcile Shelf Prices*:

- the day a **dated promotion** opens or closes on its own;
- a shelf price computed over the **cost**, which moves on the next
  reception at a different cost;
- a change of **VAT rate**, which re-splits every price in the shop;
- anything else that moved the label without anyone writing a rule.

The cron is the mechanism of record, and it is the one to trust: it
checks the invariant itself — the markup ledger says what each unit on the
shelf carries, the price list says what the label reads, and those two
agreeing is what this family of modules exists to maintain. The write
hooks only make the common cases immediate.

The cost is deliberately not watched as it is written. `standard_price`
is rewritten by the valuation on every reception under average cost, and
hanging a price check off the hot path of every goods movement would make
every receipt pay for a check that almost never finds anything.

Stock the markup ledger does not yet account for is left alone by the
reconciliation. That is the opening balance, it has its own wizard, and a
document raised over it would refuse to post anyway.

## One open draft per shop

A shop has at most one open automatic document. A second price move on the
same goods brings the open draft up to date instead of raising another
one, so three price moves in a morning are one document quoting the price
that is actually on the label — and the nightly reconciliation does not
add the same divergence again every night until somebody posts it.

## Posting does not replace your price rules

Posting writes a fixed rule per variant only where the price list does not
already answer with the price the document decided. A document raised *by*
a category rule or a markup formula therefore writes nothing back: the
rule that produced the price still reaches the product afterwards. A fixed
rule is an override, and it is written when somebody actually overrode
something — a price typed by hand on the document.
