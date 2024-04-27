from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError
class ItemFee(models.Model):
    _name = 'item.fee'
    _rec_name = 'name'

    code = fields.Char('Mã phí', required=True)
    name = fields.Char('Tên phí', required=True)
    fee_group_id = fields.Many2one('fee.group', 'Nhóm Phí')