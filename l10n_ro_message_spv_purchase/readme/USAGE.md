1. Open an SPV message and make sure the partner is set.
2. Check `Purchase Reference` (auto-filled from the XML when present) or
   `Reference`.
3. Use one of the header buttons:
   - **Find Purchase**: links and opens the only match; when several matches
     are found, opens the filtered list; when none, shows an informative
     error.
   - **Create Purchase**: searches first; when none is found, creates a draft
     purchase order for the selected partner, links it and opens it;
     otherwise behaves like **Find Purchase**.
4. After linking/creating, the module posts a note on the purchase order and
   attaches a copy of the SPV XML to it.
