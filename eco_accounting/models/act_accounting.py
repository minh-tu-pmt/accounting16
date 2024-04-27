from odoo import api, models, fields, SUPERUSER_ID, _
from odoo.exceptions import ValidationError


class ACT_Accounting(models.Model):
    _inherit = 'account.account'

    short_name = fields.Char(string='Tên ngắn')
    is_debt_account = fields.Boolean(string='TK công nợ')
    is_general_account = fields.Boolean(string='TK tổng hợp', store=True)
    is_detail_account = fields.Boolean(string='TK chi tiết', compute='_compute_is_detail_account')
    parent_id = fields.Many2one(comodel_name='account.account', string='TK mẹ')
    currency_id = fields.Many2one(comodel_name='res.currency', string='Đơn vị tiền tệ')
    level = fields.Integer(string='Bậc tài khoản', compute='_compute_based_on_parent_id')
    group_id = fields.Many2one(comodel_name='account.group', string='Nhóm')
    active = fields.Boolean(default=True)
    @api.depends('parent_id')
    def _compute_based_on_parent_id(self):
        for rec in self:
            # nếu bậc tk mẹ lớn nhất thì tk đó ko phải là tk tổng hợp
            if not self.env['account.account'].search([('parent_id', '=', rec.id)]):
                rec.is_general_account = False
            else:
                rec.is_general_account = True

            if rec.parent_id:
                rec.level = rec.parent_id.level + 1
            else:
                rec.level = 1


    @api.depends('is_general_account')
    def _compute_is_detail_account(self):
        for rec in self:
            rec.is_detail_account = not rec.is_general_account

    @api.model
    def create(self, vals):
        res = super(ACT_Accounting, self).create(vals)
        if res.parent_id and self.env['account.move.line'].search([('account_id', '=', res.parent_id.id)]):
            raise ValidationError(_('Không tạo được tài khoản do tài khoản mẹ của nó đã có bút toán phát sinh!'))
        return res

    def action_read_account(self):
        res = super(ACT_Accounting, self).action_read_account()
        res['view_id'] = self.env.ref('eco_accounting.act_accounting_form_view').id
        return res

    def unlink(self):
        res = super(ACT_Accounting, self).unlink()
        account = self.env['account.move.line'].sudo().search([('account_id', '=', self.id)])
        if account:
            for rec in account:
                if rec.move_id.state == 'posted':
                    raise ValidationError(_("Bạn không thể xóa tài khoản này"))
        return res
