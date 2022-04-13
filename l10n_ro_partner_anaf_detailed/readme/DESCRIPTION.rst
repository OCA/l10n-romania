For romanian companies (partner has is_company, is from Romania or has a vat starting with RO),
at each update (with module fiscal_validation or at create with partner_create_by_vat) or at press of 
"Update Anaf Data" button is refreshing the data from anaf webiste.
This module is a extenion of l10n_ro_partner_create_by_vat
If is updated daily is going to have in history all the modfiication of company state and scopvat.
If read the computed field from partner anaf_scpTVA or anaf_statusInactivi  wit anaf_date in contex will give the status from what is in database at that time
If on partner you are calling the function get_anaf_status_at_date will retun a dictionary with error if is the case if not with statusInactivi and scpTVA from anaf_date in contex if not from today 



