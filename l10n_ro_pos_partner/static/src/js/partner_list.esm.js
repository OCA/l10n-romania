import {PartnerList} from "@point_of_sale/app/screens/partner_list/partner_list";
import {_t} from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";

patch(PartnerList.prototype, {
    /**
     * The CUI behind the current search, or false when the cashier is not
     * looking for one.
     *
     * A Romanian CUI is between 2 and 10 digits, written with or without the
     * `RO` prefix depending on whether the company pays VAT -- the customer
     * reading it off an invoice will not know which of the two the shop has
     * on file, so accept both.
     */
    get l10nRoVatSearchQuery() {
        const query = (this.state.query || "").replace(/\s+/g, "").toUpperCase();
        if (!query) {
            return false;
        }
        const cui = query.startsWith("RO") ? query.slice(2) : query;
        return /^\d{2,10}$/.test(cui) ? cui : false;
    },

    /**
     * The two lines the cashier is shown when the CUI matched nothing.
     *
     * Built here rather than in the template: a sentence broken around a
     * `t-esc` is exported to translators in pieces, and no language keeps
     * the same word order as English.
     */
    get l10nRoNoPartnerMessage() {
        return _t("No customer found with VAT %s", this.l10nRoVatSearchQuery);
    },

    get l10nRoCreateFromAnafLabel() {
        return _t("Create from ANAF (VAT: %s)", this.l10nRoVatSearchQuery);
    },

    /**
     * Fetch the company from ANAF and put it on the order.
     *
     * Offered only once the local search came back empty: a customer already
     * on file is picked from the list, not fetched again.
     */
    async l10nRoCreatePartnerFromAnaf() {
        const cui = this.l10nRoVatSearchQuery;
        if (!cui) {
            return;
        }

        this.state.loading = true;
        try {
            const result = await this.pos.data.callRelated(
                "res.partner",
                "l10n_ro_pos_create_partner_from_vat",
                [this.pos.config.id, cui]
            );
            const partner = result["res.partner"]?.[0];
            if (partner) {
                this.clickPartner(partner);
            }
        } catch (error) {
            this.notification.add(
                error.data?.message ||
                    error.message ||
                    _t("Error fetching data from ANAF"),
                {type: "danger"}
            );
        } finally {
            this.state.loading = false;
        }
    },
});
