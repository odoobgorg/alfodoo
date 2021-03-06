# -*- coding: utf-8 -*-
# Copyright 2016 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import re
from openerp import api, fields, models, _
from openerp.exceptions import UserError, ValidationError


CMIS_NAME_INVALID_CHARS = r'\/:*?"<>|'
CMIS_NAME_INVALID_CHARS_RX = '[' + re.escape(CMIS_NAME_INVALID_CHARS) + ']'


class CmisBackend(models.Model):

    _inherit = 'cmis.backend'

    @api.constrains('sanitize_replace_char')
    def _check_sanitize_replace_char(self):
        for rec in self:
            rc = self.sanitize_replace_char
            if rc and re.findall(CMIS_NAME_INVALID_CHARS_RX, rc):
                raise ValidationError(
                    _("The character to use as replacement can not be one of"
                      "'%s'") % CMIS_NAME_INVALID_CHARS
                    )

    enable_sanitize_cmis_name = fields.Boolean(
        'Sanitize name on content creation?',
        help='If checked, the name of the CMIS content created by the '
             'CMIS fields will be sanitized by replacing the characters not '
             'supported in a cmis:name with the one specified.',
        default=True)
    sanitize_replace_char = fields.Char(
        'Replacement char',
        help='Character used as replacement of invalid characters found in'
             'the value to use as cmis:name by the sanitize method',
        default='_')

    @api.model
    def _get_web_description(self, record):
        """ Return the desciption of backend record to be included into the
        field description of cmis fields that reference the backend.
        """
        return {
            'id': record.id,
            'name': record.name,
            'location': record.location
        }

    @api.multi
    def get_web_description(self):
        """ Return informations to be included into the field description of
        cmis fields that reference the backend.
        """
        ret = {}
        for this in self:
            ret[this.id] = self._get_web_description(this)
        return ret

    @api.model
    def get_by_name(self, name, raise_if_not_found=True):
        # simple case: one backend
        domain = [(1, '=', 1)]
        if name:
            # multi backends case
            domain = [('name', '=', name)]
        backend = self.search(domain)
        if len(backend) != 1 and raise_if_not_found:
            if name:
                msg = _("Expected 1 backend named %s, %s found" %
                        (name, len(backend)))
            else:
                msg = _('No backend found')
            raise UserError(msg)
        return backend

    @api.model
    def is_valid_cmis_name(self, name, raise_if_invalid=False):
        if re.findall(CMIS_NAME_INVALID_CHARS_RX, name) or \
                name.startswith(' ') or \
                name.endswith(' '):
            if not raise_if_invalid:
                return False
            raise UserError(_("%s is not a valid name.\n"
                              "The following chars are not allowed %s") %
                            (name, CMIS_NAME_INVALID_CHARS))
        return True

    @api.multi
    def sanitize_cmis_name(self, value, replace_char=None):
        """Replace chars not allowed in cmis by the value of replace_char.
        If replace_char is None, the character used to subsitute invalid chars
        is the one defined by the sanitize_replace_char field
        """
        self.ensure_one()
        if replace_char is None:
            replace_char = self.sanitize_replace_char or ''
        return re.sub(CMIS_NAME_INVALID_CHARS_RX, replace_char,
                      value.strip()).strip()

    @api.multi
    def sanitize_cmis_names(self, values, replace_char=None):
        """Sanitize a list of values
        """
        return [self.sanitize_cmis_name(v, replace_char) for v in values]

    @api.multi
    def get_folder_by_path_parts(self, path_parts, create_if_not_found=True,
                                 cmis_parent_objectid=None):
        """Return the cmis object for the specified path parts.
        The path is build from path_parts where each part is sanitized if
        `enable_sanitize_cmis_name` is True on the backend instance
        """
        self.ensure_one()
        if self.enable_sanitize_cmis_name:
            path_parts = self.sanitize_cmis_names(path_parts)
        path = "/".join(path_parts)
        return self.get_folder_by_path(
            path, create_if_not_found, cmis_parent_objectid)
