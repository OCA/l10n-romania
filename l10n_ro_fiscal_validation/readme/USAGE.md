A cron is set to update partners daily.

## Configuration parameters

The bulk ANAF sync (`res.partner.update_l10n_ro_vat_subjected`) reads the
following keys from `ir.config_parameter`. All keys are optional — sensible
defaults are used when they are not set.

| Key | Default | Purpose |
| --- | --- | --- |
| `l10n_ro_fiscal_validation.anaf_bulk_url` | `https://webservicesp.anaf.ro/AsynchWebService/api/v/ws/tva` | Endpoint that receives the asynchronous bulk VAT-status request. Override only if ANAF publishes a new URL or you want to route the call through a proxy. |
| `l10n_ro_fiscal_validation.anaf_corr` | `https://webservicesp.anaf.ro/AsynchWebService/api/v8/ws/tva?id=%s` | Endpoint polled for the result of the bulk request. Must contain a single `%s` placeholder — the `correlationId` returned by the bulk call is interpolated into it. |
| `l10n_ro_fiscal_validation.anaf_bulk_number` | `499` | Maximum number of VAT numbers sent per ANAF call. Partners are split into chunks of this size before each request. ANAF currently caps a bulk request at 500 entries, so do not raise this above `499`. |
| `l10n_ro_partner_create_by_vat.anaf_api_key` | *(empty)* | API key for ANAF endpoints that require authentication. When empty, the request is sent unauthenticated. The same key is shared with the `l10n_ro_partner_create_by_vat` module, so set it once and both flows use it. |
| `l10n_ro_partner_create_by_vat.anaf_api_key_header_tag` | `x-api-key` | Name of the HTTP header that carries the API key. Only meaningful when `l10n_ro_partner_create_by_vat.anaf_api_key` is set; change it if ANAF requires a different header name (e.g. `Authorization`). |

Set these from **Settings → Technical → Parameters → System Parameters** or
via a data file / shell, e.g.:

```python
self.env["ir.config_parameter"].sudo().set_param(
    "l10n_ro_fiscal_validation.anaf_bulk_number", "200",
)
```
