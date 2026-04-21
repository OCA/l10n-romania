  - Funcționalități:

    - Limitare încasare numerar: implementează verificări pentru plafoanele de încasări în numerar, conform legislației.
      Plafoanele sunt configurabile prin parametri de sistem (`l10n_ro_accounting.amount_company_limit` implicit 5000 RON și `l10n_ro_accounting.amount_person_limit` implicit 10000 RON).
    - Afișare conturi în format scurt: conturile contabile sunt afișate într-un format simplificat (fără zerourile de umplere) și cu punct pentru separarea analiticului (ex: 401.1).
    - Corecție display name conturi: numele afișat al contului include codul formatat scurt urmat de denumire.
