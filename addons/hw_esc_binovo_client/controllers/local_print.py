# -*- coding: utf-8 -*-
# © 2018 Binovo IT Human Project SL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
import requests
from odoo import exceptions
from odoo import http, _
from odoo.http import request

_logger = logging.getLogger(__name__)

SEND_TIMEOUT = 60


def jsonrpc(params=None, printer=None, report=None, session_id=None):
    """
    Calls the provided JSON-RPC endpoint, unwraps the result and
    returns JSON-RPC errors as exceptions.
    """
    _logger.info('hw_esc_binovo_client jsonrpc %s')
    try:
        session = requests.Session()
        session.cookies['session_id'] = session_id
        req = session.get(params['report_url'],
                          cookies={'session_id': session_id})
        return printer.print_document(report, req.content,
                                      **{'tray': False, 'doc_format': 'qweb-pdf', 'action': 'server'})
    except (ValueError, requests.exceptions.ConnectionError, requests.exceptions.MissingSchema, requests.exceptions.Timeout, requests.exceptions.HTTPError) as e:
        raise exceptions.AccessError('The url that this service requested returned an error. Please contact the author the app. The url it tried to contact was ')


class PrintInClient(http.Controller):

    @http.route('/hw_esc_binovo_client/print_in_client', type='json', auth='public')
    def print_in_client(self, *args, **kwargs):
        printer = request.env['printing.printer'].search([('default', '=', True)])
        if not printer:
            raise exceptions.AccessError('No printer available!')
        report_obj = request.env.ref('stock.action_report_lot_barcode')
        url = request.env['ir.config_parameter'].get_param('server_ip')
        if not url:
            raise exceptions.AccessError('No server configured!')
        report = request.env['ir.actions.report'].browse([kwargs['report_id']])
        report_url = url + '/report/pdf/' + report.report_name + '/' + str(kwargs['docid'][0])
        params = {'report_url': report_url}
        r = jsonrpc(params=params, printer=printer, report=report_obj, session_id=kwargs['session_id'])
        return True
