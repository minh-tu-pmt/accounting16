from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError
class FeeGroup(models.Model):
    _name = 'fee.group'
    _rec_name = 'name'

    code = fields.Char('Mã nhóm', required=True)
    name = fields.Char('Tên nhóm', required=True)

    def unlink(self):
        for rec in self:
            item_group = self.env['item.fee'].search([('fee_group_id','=', rec.id)], limit=1)
            if item_group:
                raise ValidationError("Không thể xóa nhóm phí đã được sử dụng trong khoản mục phí!")
        return super(FeeGroup, self).unlink()
