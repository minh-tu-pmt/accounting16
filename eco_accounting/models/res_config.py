from odoo import fields, models, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    def action_merge_account(self):
        act_accounts = self.env['act.account'].sudo().search([])
        if act_accounts:
            for level in range(1, 6):
                for item in act_accounts.filtered(lambda x: x.level == level):
                    acc = self.env['account.account'].sudo().search(
                        [('code', '=', item.code), ('company_id', '=', self.company_id.id)])
                    if acc:
                        parent_account = self.env['account.account'].sudo().search(
                            [('code', '=', item.parent_id.code), ('company_id', '=', self.company_id.id)], limit=1) if item.parent_id else None
                        parent_account_id = parent_account.id if parent_account else False
                        acc.write({
                            'name': item.name,
                            'parent_id': parent_account_id,
                            'level': item.level,
                            'is_debt_account': item.is_debt_account,
                            'is_general_account': item.is_general_account,
                            'reconcile': item.allowed_compare,
                            'user_type_id': item.user_type_id.id,
                            # 'chart_template_id': item.chart_template_id.id
                        })
                    else:
                        parent_account = self.env['account.account'].sudo().search(
                            [('code', '=', item.parent_id.code), ('company_id', '=', self.company_id.id)],
                            limit=1) if item.parent_id else None
                        parent_account_id = parent_account.id if parent_account else False
                        acc_cr = self.env['account.account'].sudo().create({
                            'name': item.name,
                            'code': item.code,
                            'parent_id': parent_account_id,
                            'level': item.level,
                            'is_debt_account': item.is_debt_account,
                            'is_general_account': item.is_general_account,
                            'reconcile': item.allowed_compare,
                            'user_type_id': item.user_type_id.id,
                            'company_id': self.company_id.id
                            # 'chart_template_id': item.chart_template_id.id
                        })
            account_acc = self.env['account.account'].sudo().search([])
            if account_acc:
                for acc_acc in account_acc:
                    act_acc = self.env['act.account'].sudo().search([('code', '=', acc_acc.code)])
                    if act_acc:
                        pass
                    else:
                        acc_acc.write({'active': False})
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': ('Thành công'),
                    'message': "Cập nhật thành công!",
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': ('Cảnh báo'),
                    'message': "Cập nhật thất bại",
                    'type': 'danger',
                    'sticky': False,
                }
            }
