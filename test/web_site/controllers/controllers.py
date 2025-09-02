from odoo import http
from odoo.http import request

class WebExample(http.Controller):

    @http.route(['/mi-pagina'], type='http', auth="public", website=True)
    def pagina_personalizada(self, **kwargs):
        return request.render("web_site.my_custom_layout")
