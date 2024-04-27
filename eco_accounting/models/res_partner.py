from odoo import models, fields, api,_
import requests
res_partner = 'https://api.vietqr.io/v2/business/'
from odoo.exceptions import ValidationError



class ApiViettelPost(models.Model):
    _name="api.accouting.post"

    @api.model
    def get_partner_name_from_tax_id(self, method='GET', vat_name=None, params={}, payload={}):
        url = res_partner + vat_name  # Make sure 'res_partner' is defined
        headers = {'content-type': 'application/json', }
        req = requests.get(url, params=params, headers=headers)
        req.raise_for_status()
        response = req.json()
        return response

class ResPartner(models.Model):
    _inherit = 'res.partner'

    def click_mst(self):
        if self.vat:
            vat_name = self.vat
        else:
            raise ValidationError(_("Bạn phải nhập mã số thuế"))
        partner_name = self.env['api.accouting.post'].get_partner_name_from_tax_id(vat_name = vat_name)
        if partner_name.get('message') == 'Endpoint not found.':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': ('Thất bại'),
                    'message': partner_name.get('message'),
                    'type': 'danger',
                    'sticky': False,
                },
            }
        if partner_name.get('code') == '51':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': ('Thất bại'),
                    'message': partner_name.get('desc'),
                    'type': 'danger',
                    'sticky': False,
                },
            }
        elif partner_name.get('code') == '52':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': ('Thất bại'),
                    'message': partner_name.get('desc'),
                    'type': 'danger',
                    'sticky': False,
                },
            }
        else:
            self.name = partner_name.get('data').get('name')
            self.street = partner_name.get('data').get('address')
            # self.phone = partner_name.get('data').get('phone')
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': ('Thành công'),
                    'message': "Tìm kiếm thành công!",
                    'type': 'success',
                    'sticky': False,
                    'fadeout': 'slow',
                    'next': {
                        'type': 'ir.actions.act_window_close',
                    }
                },
            }


