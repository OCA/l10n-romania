/** @odoo-module **/

import {ListController} from "@web/views/list/list_controller";
import {listView} from "@web/views/list/list_view";
import {registry} from "@web/core/registry";

export class ETransportHistoryListController extends ListController {
    async onRefreshClick() {
        await this.env.services.orm.call(
            "l10n.ro.e.transport.history",
            "action_refresh"
        );
        await this.model.load();
    }
}

registry.category("views").add("e_transport_history_tree", {
    ...listView,
    Controller: ETransportHistoryListController,
    buttonTemplate: "ETransportHistory.buttons",
});
