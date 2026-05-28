import {AccountReportSearchBar} from "@account_reports/components/account_report/search_bar/search_bar";
import {patch} from "@web/core/utils/patch";

function roExternalToInternal(code) {
    if (!code) return code;

    if (code.includes(".")) {
        // În Python: odoo_code, analytic = code.split(".")
        return code;
    } else {
        const codeStr = String(code).trim();

        // if self.code and not self.code.isdigit(): return self.code
        // (Dacă conține deja puncte sau litere, îl lasă așa)
        if (!/^\d+$/.test(codeStr)) {
            return codeStr;
        }

        // if not self.code or len(self.code) < 4: return self.code
        if (codeStr.length < 4) {
            return codeStr;
        }
        // cont = self.code[:4]
        let new_code = codeStr.substring(0, 4);
        // while cont and cont[-1] == "0": cont = cont[:-1]
        while (new_code && new_code.endsWith("0")) {
            new_code = new_code.slice(0, -1);
        }
        // if self.code[4:]:
        if (codeStr.length > 4) {
            // analytic = int(self.code[4:])
            const analytic = parseInt(codeStr.substring(4), 10);
            // if analytic: cont += "." + str(analytic)
            if (analytic) {
                new_code += "." + analytic;
            }
        }
        code = new_code;
    }
    return code;
}

patch(AccountReportSearchBar.prototype, {
    async search() {
        const inputText = this.searchText.el.value.trim();
        const query = inputText.toLowerCase();
        const linesIDsMatched = [];

        await this.controller.reportLoadingPromise;

        if (query.length) {
            // Extragem primul cuvânt (codul) din textul de căutare
            // și încercăm conversia din format extern în format intern.
            const codePart = inputText.split(" ")[0];
            const internalCode = roExternalToInternal(codePart).toLowerCase();
            // Folosim fallback-ul intern doar dacă conversia a produs ceva diferit
            const useInternalFallback = internalCode !== codePart.toLowerCase();

            for (const line of this.controller.lines) {
                if (!line.name) continue;

                const lineName = line.name.trim().toLowerCase();

                // Potrivire standard (comportamentul original)
                // SAU potrivire după codul intern convertit (ex. "213004" pt. query "213.4")
                const match =
                    lineName.indexOf(query) !== -1 ||
                    (useInternalFallback && lineName.indexOf(internalCode) !== -1);

                if (match) {
                    linesIDsMatched.push(line.id);
                }
            }

            this.controller.lines_searched = linesIDsMatched;
            this.controller.updateOption("filter_search_bar", inputText);
        } else {
            delete this.controller.lines_searched;
            this.controller.deleteOption("filter_search_bar");
        }
    },
});
