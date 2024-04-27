from odoo import api, models, fields, SUPERUSER_ID, _
from odoo.exceptions import ValidationError
from datetime import datetime, date


class ActAdvance(models.Model):
    _name = 'act.advance'
    _rec_name = 'code_advance'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def _generate_code_advance(self):
        current_date = date.today()  # Use date.today() instead of datetime.date.today()
        year = str(current_date.year)
        month = str(current_date.month).zfill(2)
        records = self.search_count([('create_date', '>=', year + '-' + month + '-01 00:00:00'),
                                     ('create_date', '<=',
                                      year + '-' + month + '-' + str(current_date.day) + ' 23:59:59')])

        sequence_number = str(records + 1).zfill(5)
        return f'DNTU/{year}/{month}/{sequence_number}'

    code_advance = fields.Char(string='Số chứng từ', required=True, default=lambda self: self._generate_code_advance())
    person_sugges_id = fields.Many2one('res.users', string='Người đề nghị', default=lambda self: self.env.user,
                                       required=True)
    person_position = fields.Char(string='Chức vụ', related='person_sugges_id.partner_id.function')
    description = fields.Char('Diễn giải')
    department = fields.Char(string='Phòng ban')
    method = fields.Selection([('cash', 'Tiền mặt'), ('transfer', 'Chuyển khoản')], string="Hình thức", default='cash')
    account_bank_id = fields.Many2one('res.partner.bank', striing='Tài khoản ngân hàng', required=True)
    date_sugges = fields.Date(string='Ngày đề nghị', default=fields.Date.today, required=True)
    end_date = fields.Date(string='Hạn thanh toán', default=fields.Date.today)
    currency_id = fields.Many2one('res.currency', string='Mệnh giá')
    total_money_sugges = fields.Monetary(string='Tổng tiền đề nghị', compute='_compute_money_sugget',
                                         currency_field='currency_id', readonly=True)
    per_approve_id = fields.Many2one('res.users', string='Người phê duyệt', required=True)
    total_money_approve = fields.Monetary(string='Tổng tiền được duyệt', compute='_compute_money_approve',
                                          currency_field='currency_id', readonly=True)
    state = fields.Selection(
        [('draft', 'Dự thảo'), ('wait', 'Chờ duyệt'), ('approved', 'Đã duyệt'), ('advanced', 'Đã tạm ứng'),
         ('settled', 'Đã quyết toán'), ('cancel', 'Đã hủy')], string="Trạng thái", default='draft')
    act_advance_detail_ids = fields.One2many('act.advance.detail', 'act_advance_id', string='Chi tiết')
    count_synthetic = fields.Integer(compute="_compute_count_synthetic")

    def unlink(self):
        for rec in self:
            if rec.state == 'draft':
                raise ValidationError(_('Không thể xóa trạng thái khác dự thảo'))

    def _compute_count_synthetic(self):
        for rec in self:
            rec.count_synthetic = len(self.env['account.synthetic'].search([('act_advanced_id', '=', rec.id)]))

    @api.depends('act_advance_detail_ids')
    def _compute_money_sugget(self):
        for rec in self:
            rec.total_money_sugges = sum([d.money_sugges for d in rec.act_advance_detail_ids])

    @api.depends('act_advance_detail_ids')
    def _compute_money_approve(self):
        for rec in self:
            rec.total_money_approve = sum([d.money_approve for d in rec.act_advance_detail_ids])

    def action_btn_wait_approve(self):
        self.state = 'wait'

    def action_btn_approve(self):
        user_id = self.env.user.id
        # user = self.env["res.users"].sudo().browse(user_id)
        if user_id != self.per_approve_id.id:
            raise ValidationError(_("Bạn không phải người được phân công"))
        else:
            self.state = 'approved'

    def action_btn_reject(self):
        self.state = 'cancel'

    def action_btn_cancel(self):
        print('2')

    def action_btn_draft(self):
        self.state = 'draft'

    def action_btn_advanced(self):
        detail_account_payment_partner_ids = [
            (0, 0, {
                'account_id': self.person_sugges_id.partner_id.property_account_receivable_id.id,
                'partner_id': self.person_sugges_id.partner_id.id,
                'value': self.total_money_sugges,
            })
        ]

        context = {
            'default_partner_id': self.person_sugges_id.partner_id.id,
            'default_receiver': self.person_sugges_id.name,
            'default_description': self.description,
            'default_act_advanced_id': self.id,
            'default_payment_type_detail': 'follow_partner',
            'default_date': datetime.now().strftime('%Y-%m-%d'),
            'default_detail_account_payment_partner_ids': detail_account_payment_partner_ids,
            'default_type_pay': 'outbound',
            'default_type_journal': 'cash',
        }
        context_bank = {
            'default_partner_id': self.person_sugges_id.partner_id.id,
            'default_receiver': self.person_sugges_id.name,
            'default_description': self.description,
            'default_act_advanced_id': self.id,
            'default_payment_type_detail': 'follow_partner',
            'default_date': datetime.now().strftime('%Y-%m-%d'),
            'default_detail_account_payment_partner_ids': detail_account_payment_partner_ids,
            'default_type_pay': 'outbound',
            'default_type_journal': 'bank',
        }
        if self.method == 'cash':
            return {
                'name': 'Tạm ứng phiếu chi',
                'type': 'ir.actions.act_window',
                'res_model': 'account.synthetic',
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': self.env.ref('eco_accounting.form_view_account_synthetic_cashout').id,
                'context': context,
                'target': 'current',
            }
        else:
            return {
                'name': 'Giấy báo nợ',
                'type': 'ir.actions.act_window',
                'res_model': 'account.synthetic',
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': self.env.ref('eco_accounting.form_view_account_synthetic').id,
                'context': context_bank,
                'target': 'current',
            }

    def action_btn_settled(self):
        context = {
            'default_partner_id': self.person_sugges_id.partner_id.id,
            'default_description_setle': self.description,
            'default_act_advance_ids': [(6, 0, [self.id])],
            'default_settle_true':True,
        }
        return {
            'name': 'Quyết toán ạm ứng',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_type': 'form',
            'view_mode': 'form',
            'context': context,
            'view_id': self.env.ref('eco_accounting.form_view_account_settlement').id,
            'target': 'current',
        }

    def button_open_account_synthetic(self):
        return {
            'name': _('Phiếu Chi'),
            'res_model': 'account.synthetic',
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
            'domain': [('act_advanced_id', '=', self.id)]
        }


class ActAdvanceDetail(models.Model):
    _name = 'act.advance.detail'

    check_user_approval = fields.Boolean(string='Kiểm tra')
    content = fields.Char(string='Nội dung', required=True)
    money_sugges = fields.Monetary(string='Số tiền đề nghị', currency_field='currency_id', required=True)
    currency_id = fields.Many2one('res.currency', string='Mệnh giá', related='act_advance_id.currency_id')
    money_approve = fields.Monetary(string='Số tiền được duyệt', currency_field='currency_id')
    note = fields.Char(string='Note')
    per_approve_id = fields.Many2one('res.users', string='Người phê duyệt', related='act_advance_id.per_approve_id')
    act_advance_id = fields.Many2one('act.advance', string='Tạm ứng')
    state = fields.Selection(
        [('draft', 'Dự thảo'), ('wait', 'Chờ duyệt'), ('approved', 'Đã duyệt'), ('advanced', 'Đã tạm ứng'),
         ('settled', 'Đã quyết toán'), ('cancel', 'Hủy')], string="Trạng thái", related='act_advance_id.state')

    @api.depends('per_approve_id')
    def onchange_check(self):
        current_user = self.env.user
        if self.per_approve_id != current_user.id:
            self.check_user_approval = False
        else:
            self.check_user_approval = True


class AccountMoveSettlement(models.Model):
    _inherit = 'account.move'

    @api.model
    def create(self, vals_list):
        if 'settle_true' in vals_list and vals_list.get('settle_true'):
            date_format = "%Y-%m-%d"
            vals = []
            print(vals_list)
            if vals_list.get('detail_acccount_payment_partner_ids'):
                for rec in vals_list['detail_acccount_payment_partner_ids']:
                    line_vals_list = {
                        'name': rec[2]['description'],
                        'date_maturity': datetime.strptime(vals_list['end_payment'], date_format),
                        'amount_currency': -20000,
                        'currency_id': rec[2]['currency_id'],
                        'debit': rec[2]['value'],
                        'credit': 0.0,
                        'partner_id': rec[2]['partner_id'] if rec[2]['partner_id'] else False,
                        'account_id': rec[2]['account_id'],
                        'group_clause': 1,
                        'department_id': rec[2]['department_id'],
                        'analytic_account_id': rec[2]['analytic_account_id'],
                        'indenture_id': rec[2]['indenture_id'],
                        'item_fee_id': rec[2]['fee_group_id']
                    }
                    vals.append((0, 0, line_vals_list))
                val = {
                    'name': vals_list['description_setle'],
                    'date_maturity': datetime.strptime(vals_list['end_payment'], date_format),
                    'amount_currency': sum([x[2]['value'] for x in vals_list['detail_acccount_payment_partner_ids']]),
                    # 'currency_id': vals_list['currency_id'],
                    'debit': 0.0,
                    'credit': sum([x[2]['value'] for x in vals_list['detail_acccount_payment_partner_ids']]),
                    'partner_id': vals_list['partner_id'] if vals_list['partner_id'] else False,
                    'account_id': vals_list['account_sett_id'],
                    'group_clause': 1
                }
                vals.append((0, 0, val))
                vals_list['line_ids'] = vals
        res = super(AccountMoveSettlement, self).create(vals_list)
        return res

    def action_post(self):
        if self.settle_true:
            amount_settle = sum([x.value for x in self.detail_acccount_payment_partner_ids])
            if self.act_advance_ids:
                amount_total = 0
                for rec in self.act_advance_ids:
                    act_payment = self.env['account.synthetic'].sudo().search([('act_advanced_id', '=', rec.id)])
                    if act_payment.amount:
                        amount_total += act_payment.amount
                    rec.state = 'settled'
                context = {'default_account_move_id': self.id}
                if amount_settle == amount_total:
                    pass
                elif amount_settle > amount_total:
                    return {
                        'name': 'Thiếu tiền',
                        'type': 'ir.actions.act_window',
                        'res_model': 'act.flow.advanced',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'view_id': self.env.ref('eco_accounting.act_advance_form_wizard_view').id,
                        'context': context,
                        'target': 'new',
                    }
                elif amount_settle < amount_total:
                    return {
                        'name': 'Thừa tiền',
                        'type': 'ir.actions.act_window',
                        'res_model': 'act.flow.advanced',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'view_id': self.env.ref('eco_accounting.act_advance_form_wizard2_o_view').id,
                        'context': context,
                        'target': 'new',
                   }
        # for record in self.act_advanced_ids:
        res = super(AccountMoveSettlement, self).action_post()
        return res

    @api.onchange('state')
    def onchange_state_advanced(self):
        for rec in self:
            if rec.state == 'posted' and rec.act_advanced_ids:
                for record in rec.act_advanced_ids:
                    record.state = 'settled'