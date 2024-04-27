from odoo import models, fields, api

class AccountBook(models.Model):
    _name = "account.book.report"

    name = fields.Char(string="Tên báo cáo", required=True)
    account_id = fields.Many2one('account.account', string="Đầu tài khoản", required=True, domain=lambda self: [('account_type', '=', 'asset_cash')])