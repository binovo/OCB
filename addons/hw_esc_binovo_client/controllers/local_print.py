# -*- coding: utf-8 -*-
# © 2018 Binovo IT Human Project SL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import requests
import cups
from odoo import exceptions
from odoo import http, _
import os
from tempfile import mkstemp


def jsonrpc(params=None, session_id=None, printer=None):
    try:
        session = requests.Session()
        session.cookies['session_id'] = session_id
        req = session.get(params['report_url'],
                          cookies={'session_id': session_id})
        fd, file_name = mkstemp()
        try:
            os.write(fd, req.content)
        finally:
            os.close(fd)
        connection = cups.Connection(host='localhost', port=631)
        connection.printFile(printer, file_name, file_name, options={})
        return True
    except (ValueError, requests.exceptions.ConnectionError, requests.exceptions.MissingSchema, requests.exceptions.Timeout, requests.exceptions.HTTPError) as e:
        raise exceptions.AccessError('The url that this service requested returned an error. Please contact the author the app. The url it tried to contact was ')


class PrintInClient(http.Controller):

    @http.route('/hw_esc_binovo_client/print_in_client', type='json', auth='none', cors='*')
    def print_in_client(self, *args, **kwargs):
        report_url = kwargs['server'] + '/report/pdf/' + kwargs['report_name'] + '/' + str(kwargs['docid'][0])
        params = {'report_url': report_url}
        jsonrpc(params=params, session_id=kwargs['session_id'], printer=kwargs['printer'])
        return True
