## 18.0.1.2.0

- Fetch the exchange rates from `curs.bnr.ro`. Since 2026-08-04 the BNR moved
  its XML feeds off `www.bnr.ro`: the daily URL now returns the BNR homepage as
  HTML and the yearly one answers with a 302 to the homepage, so every update
  failed with `SAXParseException: <unknown>:1:0: syntax error`.
