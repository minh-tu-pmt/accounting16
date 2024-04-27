from odoo import api, models, fields, SUPERUSER_ID, _

class ActAccount(models.Model):
    _name="act.account"

    code = fields.Char()
    name = fields.Char()
    parent_id = fields.Many2one('act.account',string="Tài khoản mẹ")
    level = fields.Integer()
    is_debt_account = fields.Boolean()
    is_general_account = fields.Boolean()
    account_type = fields.Selection(
        selection=[
            ("asset_receivable", "Khoản phải thu"),
            ("asset_cash", "Ngân hàng và Tiền mặt"),
            ("asset_current", "Tài sản ngắn hạn"),
            ("asset_non_current", "Tài sản dài hạn"),
            ("asset_prepayments", "Trả trước"),
            ("asset_fixed", "Tài sản cố định"),
            ("liability_payable", "Phải trả"),
            ("liability_credit_card", "Thẻ tín dụng"),
            ("liability_current", "Nợ ngắn hạn"),
            ("liability_non_current", "Nợ cố định"),
            ("equity", "Vốn chủ sở hữu"),
            ("equity_unaffected", "Thu nhập năm hiện tại"),
            ("income", "Doanh thu"),
            ("income_other", "Doanh thu khác"),
            ("expense", "Chi phí"),
            ("expense_depreciation", "Khấu hao"),
            ("expense_direct_cost", "Giá vốn hàng bán"),
            ("off_balance", "Các khoản mục ngoài bảng cân đối"),
        ],
        string="Nhóm"
    )
    allowed_compare = fields.Boolean()
    chart_template_id = fields.Many2one('account.chart.template',string="template")




