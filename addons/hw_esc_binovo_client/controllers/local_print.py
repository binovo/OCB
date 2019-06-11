# -*- coding: utf-8 -*-
# © 2018 Binovo IT Human Project SL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import requests
import cups
from odoo import http, _
import os
from tempfile import mkstemp


def jsonrpc(params=None, session_id=None, printer=None):
    try:
        session = requests.Session()
        session.cookies['session_id'] = session_id
        resp = session.get(params['report_url'],
                           cookies={'session_id': session_id})
        if 200 == resp.status_code:
            fd, file_name = mkstemp()
            try:
                os.write(fd, resp.content)
            finally:
                os.close(fd)
            connection = cups.Connection(host='localhost', port=631)
            connection.printFile(printer, file_name, file_name, options={})
            return _('Document sent to the printer.')
        else:
            if 500 == resp.status_code:
                return _('Record does not exist or has been deleted.')
            elif 404 == resp.status_code:
                return 'Report does not exist.'
            else:
                return _('Undefined error.')
    except (ValueError, requests.exceptions.ConnectionError, requests.exceptions.MissingSchema,
            requests.exceptions.Timeout, requests.exceptions.HTTPError) as e:
        return _('The url that this service requested returned an error')
    except:
        return _('Undefined error.')


class PrintInClient(http.Controller):

    @http.route('/hw_esc_binovo_client/print_in_client', type='json', auth='none', cors='*')
    def print_in_client(self, *args, **kwargs):
        if 0 < len(kwargs['docid']):
            report_url = kwargs['server'] + '/report/pdf/' + kwargs['report_name'] + '/' + str(kwargs['docid'][0])
            params = {'report_url': report_url}
            return jsonrpc(params=params, session_id=kwargs['session_id'], printer=kwargs['printer'])
        else:
            return _('Record does not exist or has been deleted.')
