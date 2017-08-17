"""
File       : Data.py
Author     : Valentin Kuznetsov <vkuznet AT gmail dot com>
Description: This module consists of all REST APIs required by MicroService

Client may invoke GET/POST calls to MicroService, e.g.
# return status of the MicroService
curl http://localhost:8822/microservice/data/status
# ping MicroService, i.e. return its default message
curl http://localhost:8822/microservice/data
# post data to MicroService
curl -X POST -H "Content-type: application/json" -d '{"request":{"spec":"spec"}}' http://localhost:8822/microservice/data
"""
# futures
from __future__ import print_function, division

# system modules
import json
import traceback
import importlib
from types import GeneratorType

# 3d party modules
import cherrypy

# WMCore modules
from WMCore.REST.Server import RESTEntity, restcall
from WMCore.REST.Tools import tools
from WMCore.REST.Validation import validate_rx, validate_str
from WMCore.REST.Format import JSONFormat

# MicroService modules
from WMCore.Services.MicroService.Manager import MicroServiceManager
from WMCore.Services.MicroService.Regexp import PAT_INFO, PAT_UID

class Data(RESTEntity):
    "REST interface for MicroService"
    def __init__(self, app, api, config, mount):
        RESTEntity.__init__(self, app, api, config, mount)
        self.config = config
        print("### config.manager", config.manager, type(config.manager))
        arr = config.manager.split('.')
        try:
            cname = arr[-1]
            module = importlib.import_module('.'.join(arr[:-1]))
            self.mgr = getattr(module, cname)(config)
        except ImportError:
            traceback.print_exc()
            self.mgr = MicroServiceManager(config)
        print("### mgr", self.mgr)

    def validate(self, apiobj, method, api, param, safe):
        """
        Validate request input data.
        Has to be implemented, otherwise the service fails to start.
        If it's not implemented correctly (e.g. just pass), the arguments
        are not passed in the method at all.

        """
        if method == 'GET':
            if len(param.args) == 1 and param.args[0] == 'status':
                safe.args.append(param.args[0])
                param.args.remove(param.args[0])
#                 validate_rx('request', param, safe, optional=True)
#                 validate_str('_', param, safe, PAT_INFO, optional=True)
                return True
            if len(param.args) == 0:
                return True
        elif method == 'POST':
            if not param.args or not param.kwargs:
                return False
        return True

    @restcall(formats=[('application/json', JSONFormat())])
    @tools.expires(secs=-1)
    def get(self, *args, **kwds):
        """
        Implement GET request with given uid or set of parameters
        All work is done by MicroServiceManager
        """
        if 'status' in args:
            return results(dict(performance=self.mgr.status(**kwds)))
        return results({'request': kwds, 'results': 'Not available', 'microservice': self.mgr.__class__.__name__})

    @restcall(formats=[('application/json', JSONFormat())])
    @tools.expires(secs=-1)
    def post(self):
        """
        Implement POST request API, all work is done by MicroServiceManager.
        The input HTTP request should be in the following form
        {"request":some_data} for posting the data into the service.
        """
        msg = 'expect "request" attribute in your request'
        result = {'status': 'Not supported, %s' % msg, 'request': None}
        try:
            data = json.load(cherrypy.request.body)
            if 'request' in data.keys():
                kwargs = data['request']
                result = self.mgr.request(**kwargs)
            return json.dumps(result)
        except cherrypy.HTTPError:
            raise
        except Exception as exp:
            msg = 'Unable to POST request, error=%s' % traceback.format_exc()
            raise cherrypy.HTTPError(status=500, message=msg)