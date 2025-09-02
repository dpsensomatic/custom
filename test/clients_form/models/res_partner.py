# -*- coding: utf-8 -*-
# Importacion de los modulos necesarios:
# - models: para definir o extender modelos existentes
# - fields: para declarar nuevos campos
# - api: para decoradores como @api.model, @api.depends, etc.
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import unicodedata
# Creacion de una clase 'clients_form' para añadir un nuevo campo de tipo CharField


class clients_form (models.Model):

    # _inherit usada para heredar un modelo
    # en este caso se debe poner el nombre del modelo del modo desarrollador
    _inherit = 'res.partner'

    # _description usada para dar una breve descripcion de lo que tratara la actualizacion de clientes en este caso
    _description = 'Clase para configurar el formulario de clientes'

    # Añadir nuevos campos al form
    # Detalles De La Dirección-creados por mi
    full_address = fields.Text(string=('Dirección completa'))
    shipping_address = fields.Text(string=('Dirección de envío'))
    billing_email = fields.Char(string=('Correo facturación'))
    billing_close = fields.Char(string=('Cierre facturación'))
    tax_certificates = fields.Char(string=('Certificados tributarios'))
    certificate_details = fields.Char(string=('Detalles certificados'))

    # Detalles De La Dirección-creados por odoo
    # city = placeholder='Ciudad'
    # country_id = placeholder='Pais'

    # Detalles del cliente
    # Nombre del cliente odoo (required)
    # Industria odoo

    # Teléfono odoo phone reposicionar
    # celular odoo mobile ocultar
    # Correo odoo
    # Página Web odoo
    # Nit odoo Vat reposicionar
    # Clasificación
    clasification = fields.Many2one(
        'clasification.options',
        string='Clasificación',
        required=True
    )
    # Fecha de Nacimiento
    birth_date = fields.Date(string=('Fecha de nacimiento'))
    # Comentarios Clasificación
    classification_comments = fields.Char()
    # Asignado a
    assigned_to = fields.Many2one(
        'hr.employee',
        string='Asignado a',
        help='Empleado responsable de atender este cliente',
        required=True
    )
    # Atendido por
    # Campo llamado: 'attended_by', Tipo Char, Label: 'atendido por'
    attended_by = fields.Char(string=('Atendido por'))
    # Origen de cliente
    customer_source = fields.Many2one(
        'customer.source.options',
        string='Tipo de origen del cliente',
        required=True
    )
    # Forma de pago
    payment_method = fields.Char(string=('Forma de pago'), required=True)
    # RdStation Id
    rdstation_id = fields.Char(string=('RdStation Id'))
    # Importancia
    importance = fields.Many2one(
        'importance.level',
        string='Importancia',
        help='Nivel de importancia del cliente',
    )
    

    @api.onchange('full_address')
    def _onchange_full_address(self):
        for partner in self:
            if partner.full_address:
                partes = [p.strip() for p in partner.full_address.split(',')]

                if len(partes) >= 1:
                    partner.street = partes[0]
                
                if len(partes) >= 2:
                    partner.street2 = partes[1]

                if len(partes) >= 3:
                    partner.city = partes[2]

                if len(partes) >= 4:
                # Debes buscar el ID del estado
                    state_name = (partes[3])
                    state = self.env['res.country.state'].search(
                    [('name', 'ilike', state_name)], limit=1)
                    if not state:
                        raise ValidationError(f"No se encontró el Estado: '{state_name}'")
                    partner.state_id = state

                if len(partes) >= 5:
                    country_name = (partes[4])
                    country = self.env['res.country'].search(
                        [('name', 'ilike', country_name)], limit=1)
                    if not country:
                        raise ValidationError(f"No se encontró el país: '{country_name}'")
                    partner.country_id = country


class ImportanceLevel(models.Model):
    _name = 'importance.level'
    _description = 'Niveles de Importancia'

    name = fields.Char(string=('Nivel de Importancia'), required=True)


class CustomerSourceOptions(models.Model):
    _name = 'customer.source.options'
    _description = 'Origen de los clientes'

    name = fields.Char(string=('Origen del cliente'), required=True)



class ClasificationOptions(models.Model):
    _name = 'clasification.options'
    _description = 'Clasificación de los clientes'

    name = fields.Char(string=('Clasificación del cliente'), required=True)


