#-------------------------------------------------------------------------------
#
# Handles the WPS requests to the VirES server
#
# Authors: Ashley Smith <ashley.smith@ed.ac.uk>
#          Martin Paces <martin.paces@eox.at>
#
#-------------------------------------------------------------------------------
# Copyright (C) 2018 EOX IT Services GmbH
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies of this Software or works derived from this Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#-------------------------------------------------------------------------------


import datetime
import json
from tqdm import tqdm

from ._wps.wps_vires import ViresWPS10Service
# from .wps.time_util import parse_datetime
from ._wps.http_util import encode_basic_auth
from logging import getLogger, DEBUG, INFO, WARNING, ERROR, CRITICAL
from ._wps.log_util import set_stream_handler
# from jinja2 import Environment, FileSystemLoader
from ._wps.environment import JINJA2_ENVIRONMENT
from ._wps import time_util
from ._wps.wps import WPSError

from ._data_handling import ReturnedData

LEVELS = {
    "DEBUG": DEBUG,
    "INFO": INFO,
    "WARNING": WARNING,
    "ERROR": ERROR,
    "NO_LOGGING": CRITICAL + 1,
}


def get_log_level(level):
    if isinstance(level, str):
        return LEVELS[level]
    else:
        return level


def wps_xml_request(templatefile, inputs):
    """Creates a WPS request object that can later be executed

    Args:
     templatefile (str): Name of the xml template file
     input (WPSInputs): Contains valid parameters to fill the template
    """
    template = JINJA2_ENVIRONMENT.get_template(templatefile)
    request = template.render(**inputs.as_dict).encode('UTF-8')
    return request


class WPSInputs(object):
    """Holds the set of inputs to be passed to the request template
    """

    def __init__(self):
        pass


class ProgressBar(object):
    """Generates a progress bar from the WPS status.
    """

    def __init__(self):
        self.percentCompleted = 0
        self.lastpercent = 0

        l_bar = 'Processing: {percentage:3.0f}%|'
        bar = '{bar}'
        r_bar = '|  [ Elapsed: {elapsed}, Remaining: {remaining} {postfix}]'
        bar_format = '{}{}{}'.format(l_bar, bar, r_bar)
        self.tqdm_pbar = tqdm(total=100, bar_format=bar_format)

        self.refresh_tqdm()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.cleanup()

    def cleanup(self):
        self.tqdm_pbar.close()

    def update(self, wpsstatus):
        """Updates the internal state based on the state of a WPSStatus object.
        """
        self.lastpercent = self.percentCompleted
        self.percentCompleted = wpsstatus.percentCompleted
        if self.lastpercent != self.percentCompleted:
            self.refresh_tqdm()

    def refresh_tqdm(self):
        """Updates the output of the progress bar.
        """
        if self.percentCompleted is None:
            return
        self.tqdm_pbar.update(self.percentCompleted-self.lastpercent)
        if self.percentCompleted == 100:
            self.cleanup()
            print('Downloading...')


class ClientRequest(object):
    """Handles the requests to and downloads from the server.

    See SwarmClientRequest
    """

    def __init__(self, url=None, username=None, password=None,
                 logging_level="NO_LOGGING", server_type="Swarm"):

        for i in [url, username, password]:
            if not isinstance(i, str):
                raise TypeError(
                    "url, username, and password must all be strings"
                )

        self._server_type = server_type
        self._request_inputs = None
        self._templatefiles = None
        self._supported_filetypes = None

        logging_level = get_log_level(logging_level)
        self._logger = getLogger()
        set_stream_handler(self._logger, logging_level)

        # service proxy with basic HTTP authentication
        self._wps_service = ViresWPS10Service(
            url,
            encode_basic_auth(username, password),
            logger=self._logger
        )

    def __str__(self):
        return "Request details:\n{}".format('\n'.join(
            ['{}: {}'.format(key, value) for (key, value) in
             self._request_inputs.as_dict.items()
             ]))

    def get_between(self, start_time, end_time, filetype="csv", asynchronous=True):
        """Make the server request and download the data.

        Args:
            start_time (datetime)
            end_time (datetime)
            filetype (str): one of ('csv', 'cdf')
            asynchronous (bool): True for asynchronous processing, False for synchronous

        Returns:
            ReturnedData object

        """

        if asynchronous not in [True, False]:
            raise TypeError("asynchronous must be set to either True or False")

        # Initialise the ReturnedData so that filetype checking is done there
        retdata = ReturnedData(filetype=filetype)

        if retdata.filetype not in self._supported_filetypes:
            raise TypeError("filetype: {} not supported by server"
                            .format(filetype)
                            )
        if retdata.filetype == "csv":
            response_type = "text/csv"
        elif retdata.filetype == "cdf":
            response_type = "application/x-cdf"

        if asynchronous:
            # asynchronous WPS request
            templatefile = self._templatefiles['async']
        else:
            # synchronous WPS request
            templatefile = self._templatefiles['sync']

        # Finalise the WPSInputs object
        self._request_inputs.begin_time = start_time
        self._request_inputs.end_time = end_time
        self._request_inputs.response_type = response_type

        self._request = wps_xml_request(templatefile, self._request_inputs)

        print(self)

        try:
            if asynchronous:
                with ProgressBar() as progressbar:
                    response = self._wps_service.retrieve_async(
                        self._request, status_handler=progressbar.update
                    )
            else:
                response = self._wps_service.retrieve(self._request)
        except WPSError:
            raise RuntimeError("Server error - may be outside of product availability")

        retdata.data = response
        return retdata
