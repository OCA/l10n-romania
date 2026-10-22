Put the VAT number in the partner's form and if it's a romanian company,
it will fetch data available on ANAF website.

# Configuration parameters

The ANAF lookup (`res.partner._get_Anaf`) reads the following keys from
`ir.config_parameter`. All keys are optional — sensible defaults are used
when they are not set.

| Key | Default | Purpose |
| --- | --- | --- |
| `l10n_ro_partner_create_by_vat.anaf_url` | `https://webservicesp.anaf.ro/api/PlatitorTvaRest/v9/tva` | Endpoint queried for a single VAT number (or a small list). Override only if ANAF publishes a new URL or you want to route the call through a proxy. |
| `l10n_ro_partner_create_by_vat.anaf_api_key` | *(empty)* | API key for ANAF endpoints that require authentication. When empty, the request is sent unauthenticated. The same key is reused by the bulk sync in `l10n_ro_fiscal_validation`, so set it once and both flows use it. |
| `l10n_ro_partner_create_by_vat.anaf_api_key_header_tag` | `x-api-key` | Name of the HTTP header that carries the API key. Only meaningful when `l10n_ro_partner_create_by_vat.anaf_api_key` is set; change it if ANAF requires a different header name (e.g. `Authorization`). |

Set these from **Settings → Technical → Parameters → System Parameters** or
via a data file / shell, e.g.:

```python
self.env["ir.config_parameter"].sudo().set_param(
    "l10n_ro_partner_create_by_vat.anaf_api_key", "your-key-here",
)
```
