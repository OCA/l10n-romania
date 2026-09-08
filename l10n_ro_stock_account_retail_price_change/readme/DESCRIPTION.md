# Romania - Retail Price Change (Proces Verbal de Schimbare Pret)

Adds the price change document to the retail merchandise accounting of
`l10n_ro_stock_account_retail`.

`l10n.ro.retail.price.change` is a persistent document numbered
`PVSP/YYYY/00000` out of a sequence of its own company. It captures the
warehouse, the date, the products on hand and the old versus new shelf
price (PVA, VAT included) per line, with the markup (378) and deferred
VAT (4428) split.

The old side is what the stock carries — cost, markup and deferred VAT
per unit, read from the markup ledger — and it is read again when the
document is posted, so the delta always measures the gap that exists at
the moment the entry is made. A posted document is final: it is revoked
by posting another one, never reset, cancelled or deleted.

There are two flows:

1. **Manual** - create a draft, load the products on hand, edit the new
   prices, then post. Posting writes the new prices on the warehouse
   retail pricelist, books the revaluation and records it in the markup
   ledger, so the next sale releases the new markup and not the old one.
2. **Automatic** - when a `product.pricelist.item` on a retail pricelist
   is created or its price is modified, a draft document is raised for
   each affected retail warehouse that has stock on hand. The user
   reviews it and posts it.

## Report

The document prints as *Proces-verbal privind modificarea pretului de
vanzare cu amanuntul*, listing quantity, old and new price, old and new
value and the difference per product, with the markup and VAT split
shown separately.

## Price history

Every posted document is a dated record of the shelf price of the
products it covers. The *Price History* button on a product shows the
lines that concern it, oldest first, so the sequence of shelf prices and
the document that decided each of them are visible in one place.
