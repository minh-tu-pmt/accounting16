from odoo import api, models, fields, SUPERUSER_ID, _
from odoo.exceptions import ValidationError


class ActIndenture(models.Model):
    _name = 'act.indenture'
    _rec_name='code_inden'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    code_inden = fields.Char(string="Mã khế ước", tracking=True, required=True)
    name_inden = fields.Char(string="Tên khế ước", tracking=True, required=True)
    type_inden = fields.Selection([
        ('borrow', 'Đi vay'),
        ('loan', 'Cho vay'), ], default='borrow', string="Loại khế ước", tracking=True, required=True)
    num_inden = fields.Char(string="Số khế ước", required=True)
    date_inden = fields.Date(string="Ngày khế ước", tracking=True)
    date_br_loan = fields.Date(string="Ngày vay / cho vay", tracking=True)
    end_inden = fields.Date(string="Ngày đáo hạn", tracking=True)
    account_id = fields.Many2one('account.account', string="Tài khoản", required=True, domain="[('is_general_account', '=', False)]", tracking=True)
    partner_id = fields.Many2one('res.partner', string="Đối tác", required=True, tracking=True)
    uom_currency_id = fields.Many2one('res.currency', string="Đơn vị tiền tệ", required=True, tracking=True)
    foreign_currency_vl = fields.Monetary(string="Giá trị ngoại tệ", currency_field="uom_currency_id", tracking=True)
    value = fields.Monetary(string="Giá trị", currency_field="uom_currency_id", tracking=True)
    state = fields.Selection([
        ('non_active', 'Không sử dụng'),
        ('active', 'Sử dụng'), ], default='active', string="Trạng thái", tracking=True, required=True)
    act_performent_ids = fields.One2many('act.performent', 'act_indenture_id', string="Lãi suất", tracking=True)
    act_payment_inden_ids = fields.One2many('act.payment_inden', 'act_indenture_id', string="Thông tin thanh toán", tracking=True)

    @api.model
    def create(self, vals):
        res = super(ActIndenture, self).create(vals)
        act_indenture = self.env['act.indenture'].sudo().search([('code_inden', '=', vals.get('code_inden'))])
        if act_indenture:
            if len(act_indenture) > 1:
                raise ValidationError(_("Mã không phép trùng"))
        return res

    def unlink(self):
        for rec in self:
            account = self.env['account.move.line'].sudo().search([('account_id', '=', rec.account_id.id)])
            if account:
                for move_line in account:
                    if move_line.move_id.state == 'posted':
                        raise ValidationError(_("Bạn không thể xóa khế ước này"))
        return super(ActIndenture, self).unlink()

class ActPerforment(models.Model):
    _name = 'act.performent'

    date_active = fields.Date(string="Ngày hiệu lực")
    core_performance = fields.Float(string="Lãi suất (%)")
    act_indenture_id = fields.Many2one('act.indenture', string="Khế ước")


class ActPaymentInden(models.Model):
    _name = 'act.payment_inden'

    date_pay = fields.Date(string="Ngày thanh toán")
    foreign_currency_money = fields.Monetary(string="Tiền thanh toán ngoại tệ",currency_field='uom_currency_id')
    uom_currency_id = fields.Many2one('res.currency', string="Đơn vị tiền tệ",related='act_indenture_id.uom_currency_id')
    money_pay = fields.Monetary(string="Tiền thanh toán", currency_field='uom_currency_id')
    act_indenture_id = fields.Many2one('act.indenture', string="Khế ước")
