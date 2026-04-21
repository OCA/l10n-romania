Acest modul permite crearea și actualizarea automată a partenerilor (persoane juridice) pe baza codului de identificare fiscală (CUI/CIF), utilizând serviciile web ANAF:

  - Funcționalități:

    - Creare partener după CUI: permite introducerea codului fiscal și preluarea automată a datelor oficiale.
    - Actualizare automată date: completează denumirea, adresa completă (județ, localitate, stradă), numărul de înregistrare la Registrul Comerțului, codul poștal, telefonul și codul CAEN.
    - Integrare cu API ANAF: utilizează versiunea actualizată a serviciului web ANAF pentru verificarea stării plătitorilor de TVA.
    - Monitorizare istoric TVA și stare inactivitate:
      - Menține un istoric al perioadelor în care partenerul a fost plătitor de TVA (scpTVA).
      - Monitorizează starea de inactivitate a companiei conform registrelor ANAF.
    - Normalizare date: corecție automată a caracterelor cu sedilă în caractere cu virgulă (conform standardelor românești) pentru datele preluate.
    - Protecție date manuale: permite definirea unui "nume vechi" (`l10n_ro_old_name`) pentru a preveni suprascrierea în cazul în care utilizatorul dorește să păstreze o denumire specifică.
    - Suport pentru localități (l10n_ro_city): integrare cu nomenclatorul de localități pentru o mapare corectă a adreselor.
