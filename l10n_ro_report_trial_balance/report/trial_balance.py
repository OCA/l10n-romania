# Copyright (C) 2018 FOREST AND BIOMASS ROMANIA SA
# Copyright (C) 2021 NextERP Romania SRL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class RomaniaTrialBalanceReport(models.TransientModel):
    _name = "report.l10n_ro_report_trial_balance.trial_balance"
    _inherit = "report.account_financial_report.trial_balance"
    _description = "Romania - Trial Balance Report"

    # def _get_html(self):
    #     result = {}
    #     rcontext = {}
    #     context = dict(self.env.context)
    #     rcontext.update(context.get("data"))
    #     active_id = context.get("active_id")
    #     wiz = self.env["open.items.report.wizard"].browse(active_id)
    #     rcontext["o"] = wiz
    #     result["html"] = self.env.ref(
    #         "l10n_ro_report_trial_balance.report_trial_balance"
    #     ).render(rcontext)
    #     return result

    @api.model
    def _compute_account_amount(
        self,
        total_amount,
        tb_initial_acc,
        opening_domain_acc,
        initial_domain_acc,
        period_domain_acc,
        total_domain_acc,
    ):
        for tb in tb_initial_acc:
            acc_id = tb["account_id"]
            total_amount[acc_id] = {}
            opening_element = list(
                filter(
                    lambda acc_dict: acc_dict["account_id"][0] == acc_id,
                    opening_domain_acc,
                )
            )
            initial_element = list(
                filter(
                    lambda acc_dict: acc_dict["account_id"][0] == acc_id,
                    initial_domain_acc,
                )
            )
            period_element = list(
                filter(
                    lambda acc_dict: acc_dict["account_id"][0] == acc_id,
                    period_domain_acc,
                )
            )
            total_element = list(
                filter(
                    lambda acc_dict: acc_dict["account_id"][0] == acc_id,
                    total_domain_acc,
                )
            )
            balance = (
                (total_element[0]["debit"] - total_element[0]["credit"])
                if total_element
                else 0
            )
            total_amount[acc_id]["credit_opening"] = (
                -1 * opening_element[0]["balance"]
                if opening_element and opening_element[0]["balance"] < 0
                else 0
            )
            total_amount[acc_id]["debit_opening"] = (
                opening_element[0]["balance"]
                if opening_element and opening_element[0]["balance"] > 0
                else 0
            )
            total_amount[acc_id]["credit_initial"] = (
                initial_element[0]["credit"] if initial_element else 0
            )
            total_amount[acc_id]["debit_initial"] = (
                initial_element[0]["debit"] if initial_element else 0
            )
            total_amount[acc_id]["credit"] = (
                period_element[0]["credit"] if period_element else 0
            )
            total_amount[acc_id]["debit"] = (
                period_element[0]["debit"] if period_element else 0
            )
            total_amount[acc_id]["credit_total"] = (
                total_element[0]["credit"] if total_element else 0
            )
            total_amount[acc_id]["debit_total"] = (
                total_element[0]["debit"] if total_element else 0
            )
            total_amount[acc_id]["credit_balance"] = -balance if balance < 0 else 0
            total_amount[acc_id]["debit_balance"] = balance if balance > 0 else 0

        for tb in tb_initial_acc:
            acc_id = tb["account_id"]
            if acc_id not in total_amount.keys():
                total_amount[acc_id] = {}
                total_amount[acc_id]["credit_opening"] = 0.0
                total_amount[acc_id]["debit_opening"] = 0.0
                total_amount[acc_id]["credit_initial"] = 0.0
                total_amount[acc_id]["debit_initial"] = 0.0
                total_amount[acc_id]["credit"] = 0.0
                total_amount[acc_id]["debit"] = 0.0
                total_amount[acc_id]["credit_total"] = 0.0
                total_amount[acc_id]["debit_total"] = 0.0
                total_amount[acc_id]["credit_balance"] = 0.0
                total_amount[acc_id]["debit_balance"] = 0.0

        return total_amount

    def _get_balances_at_date_ml_domain(
        self,
        account_ids,
        journal_ids,
        company_id,
        date_from,
        only_posted_moves,
        include_date=False,
    ):
        accounts_domain = [
            ("company_id", "=", company_id),
        ]
        if account_ids:
            accounts_domain += [("id", "in", account_ids)]
        if include_date:
            domain = [("date", "<=", date_from)]
        else:
            domain = [("date", "<", date_from)]

        accounts = self.env["account.account"].search(accounts_domain)
        domain += [("account_id", "in", accounts.ids)]
        if company_id:
            domain += [("company_id", "=", company_id)]
        if journal_ids:
            domain += [("journal_id", "in", journal_ids)]
        if only_posted_moves:
            domain += [("move_id.state", "=", "posted")]
        return domain

    @api.model
    def _get_data(
        self,
        account_ids,
        journal_ids,
        company_id,
        date_to,
        date_from,
        only_posted_moves,
        hide_account_at_0,
        unaffected_earnings_account,
        fy_start_date,
        show_off_balance_accounts,
    ):
        accounts_domain = [("company_id", "=", company_id)]
        if account_ids:
            accounts_domain += [("id", "in", account_ids)]
        if not show_off_balance_accounts:
            off_balance_type = self.env.ref("account.data_account_off_sheet")
            if off_balance_type:
                accounts_domain += [("user_type_id", "!=", off_balance_type.id)]
        accounts = self.env["account.account"].search(accounts_domain)
        tb_initial_acc = []
        for account in accounts:
            tb_initial_acc.append(
                {
                    "account_id": account.id,
                    "credit_opening": 0.0,
                    "debit_opening": 0.0,
                    "credit_initial": 0.0,
                    "debit_initial": 0.0,
                    "credit": 0.0,
                    "debit": 0.0,
                    "credit_total": 0.0,
                    "debit_total": 0.0,
                    "credit_balance": 0.0,
                    "debit_balance": 0.0,
                    "amount_currency": 0.0,
                }
            )
        opening_domain = self._get_balances_at_date_ml_domain(
            account_ids,
            journal_ids,
            company_id,
            fy_start_date,
            only_posted_moves,
        )
        opening_domain_acc = self.env["account.move.line"].read_group(
            domain=opening_domain,
            fields=["account_id", "balance", "amount_currency"],
            groupby=["account_id"],
        )

        initial_domain = self._get_period_ml_domain(
            account_ids,
            journal_ids,
            None,
            company_id,
            date_from,
            fy_start_date,
            only_posted_moves,
            None,
        )
        initial_domain_acc = self.env["account.move.line"].read_group(
            domain=initial_domain,
            fields=["account_id", "debit", "credit", "balance", "amount_currency"],
            groupby=["account_id"],
        )

        period_domain = self._get_period_ml_domain(
            account_ids,
            journal_ids,
            None,
            company_id,
            date_to,
            date_from,
            only_posted_moves,
            None,
        )
        period_domain_acc = self.env["account.move.line"].read_group(
            domain=period_domain,
            fields=["account_id", "debit", "credit", "balance", "amount_currency"],
            groupby=["account_id"],
        )

        total_domain = self._get_balances_at_date_ml_domain(
            account_ids,
            journal_ids,
            company_id,
            date_to,
            only_posted_moves,
            include_date=True,
        )
        total_domain_acc = self.env["account.move.line"].read_group(
            domain=total_domain,
            fields=["account_id", "debit", "credit", "balance", "amount_currency"],
            groupby=["account_id"],
        )

        for account_rg in tb_initial_acc:
            element = list(
                filter(
                    lambda acc_dict: acc_dict["account_id"] == account_rg["account_id"],
                    total_domain_acc,
                )
            )
            if element:
                element[0]["amount_currency"] += account_rg["amount_currency"]
        total_amount = {}

        total_amount = self._compute_account_amount(
            total_amount,
            tb_initial_acc,
            opening_domain_acc,
            initial_domain_acc,
            period_domain_acc,
            total_domain_acc,
        )
        if hide_account_at_0:
            new_total_amount = {}
            for key, value in total_amount.items():
                if (
                    value["debit_opening"] != 0
                    or value["credit_opening"] != 0
                    or value["debit_initial"] != 0
                    or value["credit_initial"] != 0
                    or value["debit"] != 0
                    or value["credit"] != 0
                    or value["debit_total"] != 0
                    or value["credit_total"] != 0
                    or value["debit_balance"] != 0
                    or value["credit_balance"] != 0
                ):
                    new_total_amount[key] = value
            total_amount = new_total_amount

        accounts_ids = list(total_amount.keys())
        unaffected_id = unaffected_earnings_account
        if unaffected_id not in accounts_ids:
            accounts_ids.append(unaffected_id)
            total_amount[unaffected_id] = {}
            total_amount[unaffected_id]["debit_opening"] = 0.0
            total_amount[unaffected_id]["credit_opening"] = 0.0
            total_amount[unaffected_id]["debit_initial"] = 0.0
            total_amount[unaffected_id]["credit_initial"] = 0.0
            total_amount[unaffected_id]["debit"] = 0.0
            total_amount[unaffected_id]["credit"] = 0.0
            total_amount[unaffected_id]["debit_total"] = 0.0
            total_amount[unaffected_id]["credit_total"] = 0.0
            total_amount[unaffected_id]["debit_balance"] = 0.0
            total_amount[unaffected_id]["credit_balance"] = 0.0

        accounts_data = self._get_accounts_data(accounts_ids)
        # pl_initial_balance, pl_initial_currency_balance = self._get_pl_initial_balance(
        #     account_ids,
        #     journal_ids,
        #     None,
        #     company_id,
        #     fy_start_date,
        #     only_posted_moves,
        #     None,
        #     None,
        # )
        # if foreign_currency:
        #     total_amount[unaffected_id][
        #         "ending_currency_balance"
        #     ] += pl_initial_currency_balance
        #     total_amount[unaffected_id][
        #         "initial_currency_balance"
        #     ] += pl_initial_currency_balance
        return (
            total_amount,
            accounts_data,
        )

    def _get_hierarchy_groups(
        self, group_ids, groups_data, old_groups_ids, foreign_currency
    ):
        new_parents = False
        for group_id in group_ids:
            if groups_data[group_id]["parent_id"]:
                new_parents = True
                nw_id = groups_data[group_id]["parent_id"]
                if nw_id in groups_data.keys():
                    groups_data[nw_id]["debit_opening"] += groups_data[group_id][
                        "debit_opening"
                    ]
                    groups_data[nw_id]["credit_opening"] += groups_data[group_id][
                        "credit_opening"
                    ]
                    groups_data[nw_id]["debit_initial"] += groups_data[group_id][
                        "debit_initial"
                    ]
                    groups_data[nw_id]["credit_initial"] += groups_data[group_id][
                        "credit_initial"
                    ]
                    groups_data[nw_id]["debit"] += groups_data[group_id]["debit"]
                    groups_data[nw_id]["credit"] += groups_data[group_id]["credit"]
                    groups_data[nw_id]["debit_total"] += groups_data[group_id][
                        "debit_total"
                    ]
                    groups_data[nw_id]["credit_total"] += groups_data[group_id][
                        "credit_total"
                    ]
                    groups_data[nw_id]["debit_balance"] += groups_data[group_id][
                        "debit_balance"
                    ]
                    groups_data[nw_id]["credit_balance"] += groups_data[group_id][
                        "credit_balance"
                    ]
                else:
                    groups_data[nw_id] = {}
                    groups_data[nw_id]["debit_opening"] = groups_data[group_id][
                        "debit_opening"
                    ]
                    groups_data[nw_id]["credit_opening"] = groups_data[group_id][
                        "credit_opening"
                    ]
                    groups_data[nw_id]["debit_initial"] = groups_data[group_id][
                        "debit_initial"
                    ]
                    groups_data[nw_id]["credit_initial"] = groups_data[group_id][
                        "credit_initial"
                    ]
                    groups_data[nw_id]["debit"] = groups_data[group_id]["debit"]
                    groups_data[nw_id]["credit"] = groups_data[group_id]["credit"]
                    groups_data[nw_id]["debit_total"] = groups_data[group_id][
                        "debit_total"
                    ]
                    groups_data[nw_id]["credit_total"] = groups_data[group_id][
                        "credit_total"
                    ]
                    groups_data[nw_id]["debit_balance"] = groups_data[group_id][
                        "debit_balance"
                    ]
                    groups_data[nw_id]["credit_balance"] = groups_data[group_id][
                        "credit_balance"
                    ]

        if new_parents:
            nw_groups_ids = []
            for group_id in list(groups_data.keys()):
                if group_id not in old_groups_ids:
                    nw_groups_ids.append(group_id)
                    old_groups_ids.append(group_id)
            groups = self.env["account.group"].browse(nw_groups_ids)
            for group in groups:
                groups_data[group.id].update(
                    {
                        "id": group.id,
                        "code": group.code_prefix_start,
                        "name": group.name,
                        "parent_id": group.parent_id.id,
                        "parent_path": group.parent_path,
                        "complete_code": group.complete_code,
                        "account_ids": group.compute_account_ids.ids,
                        "type": "group_type",
                    }
                )
            groups_data = self._get_hierarchy_groups(
                nw_groups_ids, groups_data, old_groups_ids, None
            )
        return groups_data

    def _get_groups_data(self, accounts_data, total_amount, foreign_currency):
        accounts_ids = list(accounts_data.keys())
        accounts = self.env["account.account"].browse(accounts_ids)
        account_group_relation = {}
        for account in accounts:
            accounts_data[account.id]["complete_code"] = (
                account.group_id.complete_code if account.group_id.id else ""
            )
            if account.group_id.id:
                if account.group_id.id not in account_group_relation.keys():
                    account_group_relation.update({account.group_id.id: [account.id]})
                else:
                    account_group_relation[account.group_id.id].append(account.id)
        groups = self.env["account.group"].browse(account_group_relation.keys())
        groups_data = {}
        for group in groups:
            groups_data.update(
                {
                    group.id: {
                        "id": group.id,
                        "code": group.code_prefix_start,
                        "name": group.name,
                        "parent_id": group.parent_id.id,
                        "parent_path": group.parent_path,
                        "type": "group_type",
                        "complete_code": group.complete_code,
                        "account_ids": group.compute_account_ids.ids,
                        "credit_opening": 0.0,
                        "debit_opening": 0.0,
                        "credit_initial": 0.0,
                        "debit_initial": 0.0,
                        "credit": 0.0,
                        "debit": 0.0,
                        "credit_total": 0.0,
                        "debit_total": 0.0,
                        "credit_balance": 0.0,
                        "debit_balance": 0.0,
                    }
                }
            )

        for group_id in account_group_relation.keys():
            for account_id in account_group_relation[group_id]:
                groups_data[group_id]["debit_opening"] += total_amount[account_id][
                    "debit_opening"
                ]
                groups_data[group_id]["credit_opening"] += total_amount[account_id][
                    "credit_opening"
                ]
                groups_data[group_id]["debit_initial"] += total_amount[account_id][
                    "debit_initial"
                ]
                groups_data[group_id]["credit_initial"] += total_amount[account_id][
                    "credit_initial"
                ]
                groups_data[group_id]["debit"] += total_amount[account_id]["debit"]
                groups_data[group_id]["credit"] += total_amount[account_id]["credit"]
                groups_data[group_id]["debit_total"] += total_amount[account_id][
                    "debit_total"
                ]
                groups_data[group_id]["credit_total"] += total_amount[account_id][
                    "credit_total"
                ]
                groups_data[group_id]["debit_balance"] += total_amount[account_id][
                    "debit_balance"
                ]
                groups_data[group_id]["credit_balance"] += total_amount[account_id][
                    "credit_balance"
                ]

        group_ids = list(groups_data.keys())
        old_group_ids = list(groups_data.keys())
        groups_data = self._get_hierarchy_groups(
            group_ids, groups_data, old_group_ids, foreign_currency
        )
        return groups_data

    def _get_computed_groups_data(self, accounts_data, total_amount, foreign_currency):
        groups = self.env["account.group"].search([("id", "!=", False)])
        groups_data = {}
        for group in groups:
            if group.code_prefix_start:
                len_group_code = len(group.code_prefix_start)
                groups_data.update(
                    {
                        group.id: {
                            "id": group.id,
                            "code": group.code_prefix_start,
                            "name": group.name,
                            "parent_id": group.parent_id.id,
                            "parent_path": group.parent_path,
                            "type": "group_type",
                            "complete_code": group.complete_code,
                            "account_ids": group.compute_account_ids.ids,
                            "credit_opening": 0.0,
                            "debit_opening": 0.0,
                            "credit_initial": 0.0,
                            "debit_initial": 0.0,
                            "credit": 0.0,
                            "debit": 0.0,
                            "credit_total": 0.0,
                            "debit_total": 0.0,
                            "credit_balance": 0.0,
                            "debit_balance": 0.0,
                            "initial_balance": 0.0,
                            "ending_balance": 0.0,
                        }
                    }
                )

                for account in accounts_data.values():
                    if group.code_prefix_start == account["code"][:len_group_code]:
                        acc_id = account["id"]
                        group_id = group.id
                        groups_data[group_id]["debit_opening"] += total_amount[acc_id][
                            "debit_opening"
                        ]
                        groups_data[group_id]["credit_opening"] += total_amount[acc_id][
                            "credit_opening"
                        ]
                        groups_data[group_id]["debit_initial"] += total_amount[acc_id][
                            "debit_initial"
                        ]
                        groups_data[group_id]["credit_initial"] += total_amount[acc_id][
                            "credit_initial"
                        ]
                        groups_data[group_id]["debit"] += total_amount[acc_id]["debit"]
                        groups_data[group_id]["credit"] += total_amount[acc_id][
                            "credit"
                        ]
                        groups_data[group_id]["debit_total"] += total_amount[acc_id][
                            "debit_total"
                        ]
                        groups_data[group_id]["credit_total"] += total_amount[acc_id][
                            "credit_total"
                        ]
                        groups_data[group_id]["debit_balance"] += total_amount[acc_id][
                            "debit_balance"
                        ]
                        groups_data[group_id]["credit_balance"] += total_amount[acc_id][
                            "credit_balance"
                        ]

        return groups_data

    def _get_report_values(self, docids, data):

        wizard_id = data["wizard_id"]
        company = self.env["res.company"].browse(data["company_id"])
        company_id = data["company_id"]

        journal_ids = data["journal_ids"]
        account_ids = data["account_ids"]
        date_to = data["date_to"]
        date_from = data["date_from"]
        hide_account_at_0 = data["hide_account_at_0"]
        hierarchy_on = data["hierarchy_on"]
        show_hierarchy_level = data["show_hierarchy_level"]
        # foreign_currency = data["foreign_currency"]
        only_posted_moves = data["only_posted_moves"]
        unaffected_earnings_account = data["unaffected_earnings_account"]
        fy_start_date = data["fy_start_date"]
        show_off_balance_accounts = data["show_off_balance_accounts"]
        total_amount, accounts_data = self._get_data(
            account_ids,
            journal_ids,
            company_id,
            date_to,
            date_from,
            only_posted_moves,
            hide_account_at_0,
            unaffected_earnings_account,
            fy_start_date,
            show_off_balance_accounts,
        )
        trial_balance = []

        for account_id in accounts_data.keys():
            accounts_data[account_id].update(
                {
                    "debit_opening": total_amount[account_id]["debit_opening"],
                    "credit_opening": total_amount[account_id]["credit_opening"],
                    "debit_initial": total_amount[account_id]["debit_initial"],
                    "credit_initial": total_amount[account_id]["credit_initial"],
                    "debit": total_amount[account_id]["debit"],
                    "credit": total_amount[account_id]["credit"],
                    "debit_total": total_amount[account_id]["debit_total"],
                    "credit_total": total_amount[account_id]["credit_total"],
                    "debit_balance": total_amount[account_id]["debit_balance"],
                    "credit_balance": total_amount[account_id]["credit_balance"],
                    "type": "account_type",
                }
            )

        if hierarchy_on == "relation":
            groups_data = self._get_groups_data(accounts_data, total_amount, None)
            trial_balance = list(groups_data.values())
            trial_balance += list(accounts_data.values())
            trial_balance = sorted(trial_balance, key=lambda k: k["complete_code"])
            for trial in trial_balance:
                counter = trial["complete_code"].count("/")
                trial["level"] = counter
        if hierarchy_on == "computed":
            groups_data = self._get_computed_groups_data(
                accounts_data, total_amount, None
            )
            trial_balance = list(groups_data.values())
            trial_balance += list(accounts_data.values())
            trial_balance = sorted(trial_balance, key=lambda k: k["code"])
        if hierarchy_on == "none":
            trial_balance = list(accounts_data.values())
            trial_balance = sorted(trial_balance, key=lambda k: k["code"])

        return {
            "doc_ids": [wizard_id],
            "doc_model": "trial.balance.report.wizard",
            "docs": self.env["trial.balance.report.wizard"].browse(wizard_id),
            "foreign_currency": data["foreign_currency"],
            "company_name": company.display_name,
            "company_currency": company.currency_id,
            "currency_name": company.currency_id.name,
            "fy_start_date": data["fy_start_date"],
            "date_from": data["date_from"],
            "date_to": data["date_to"],
            "only_posted_moves": data["only_posted_moves"],
            "hide_account_at_0": data["hide_account_at_0"],
            "limit_hierarchy_level": data["limit_hierarchy_level"],
            "hierarchy_on": hierarchy_on,
            "trial_balance": trial_balance,
            "total_amount": total_amount,
            "accounts_data": accounts_data,
            "show_hierarchy_level": show_hierarchy_level,
        }
