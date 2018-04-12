"""

For more details about HAChina,
https://www.hachina.io/
"""
#import asyncio
import subprocess
import shutil
import os
import time
import json

class redpoint_agent(object):

    def __init__(self, ConfigPath=None, EditPath=None, Cmd_hass='hass'):
        self._version = '0.0.7'

        if os.name == 'nt':
            self._startupinfo = subprocess.STARTUPINFO()
            self._startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        else:
            self._startupinfo = None

        self._config = {}
        if ConfigPath is None:
            self._config['config_path']=self._detectConfigPath()
        else:
            self._config['config_path']=ConfigPath

        if EditPath is None:
            self._config['editing_config_path']=self._editingConfigPath()
        else:
            self._config['editing_config_path']=EditPath

        self._Cmd_hass = Cmd_hass.split()


    def _detectConfigPath(self):
        data_dir = os.getenv('APPDATA') if os.name == 'nt' \
            else os.path.expanduser('~')
        return os.path.join(data_dir, '.homeassistant')


    def _editingConfigPath(self):
        data_dir = os.getenv('APPDATA') if os.name == 'nt' \
            else os.path.expanduser('~')
        return os.path.join(data_dir, '.haconfig_tmp')


    def _ignored_files(self,adir, filenames):
        return [filename for filename in filenames if
                (adir.endswith('deps') and filename=='man')
                or (('deps' in adir) and ('Python' in adir) and filename=='Scripts')
                or (adir.endswith('site-packages') and ('colorlog' not in filename))
                or (('custom_components' not in adir) and (filename == 'tts'))
                or filename.endswith('.swp')
                or filename.endswith('.db')
                #or filename == '__pycache__'
                ]

    def copyConfig(self):
        to = self._config['editing_config_path']
        if os.path.exists(to):
            shutil.rmtree(to)
        shutil.copytree(self._config['config_path'], to, ignore=self._ignored_files)

    def Check(self):
        cmd = self._Cmd_hass + ["--script", "check_config",
               "-c", self._config['editing_config_path']]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             stdin=subprocess.PIPE,
                             startupinfo=self._startupinfo)
        out, err = p.communicate()
        #p = yield from asyncio.create_subprocess_exec(*cmd,
        #                                              stdout=asyncio.subprocess.PIPE,
        #                                              stderr=asyncio.subprocess.PIPE,
        #                                              stdin=asyncio.subprocess.PIPE,
        #                                              )
        #out, err = yield from p.communicate()
        if(err):
            raise Exception(err)

        if os.name == "nt":
            out = out.decode('gb2312')
        else:
            out = out.decode()

        return json.dumps({
            'isOK': p.returncode == 0,
            'msg': out
            })

    def ReadConfiguration(self):
        path = os.path.join(self._config['editing_config_path'], 'configuration.yaml')
        with open(path, 'r', encoding='utf8') as configuration:
            content = configuration.read()

        return content

    def WriteConfiguration(self, content):
        path = os.path.join(self._config['editing_config_path'], 'configuration.yaml')
        with open(path, 'w', encoding='utf8') as configuration:
            configuration.write(content)

        return True

    def Publish(self):
        file_from = os.path.join(self._config['editing_config_path'] , 'configuration.yaml')
        file_to = os.path.join(self._config['config_path'] , 'configuration.yaml')
        file_backup = file_to + '.' + time.strftime('%Y%m%d%H%M%S',time.localtime(time.time()))
        shutil.copyfile(file_to, file_backup)
        shutil.copyfile(file_from, file_to)
        return True


    @property
    def config(self):
        return self._config

    @property
    def version(self):
        return self._version


import logging
import asyncio
from aiohttp import web
import json
import uuid
import importlib
import sys

import voluptuous as vol
try:
    from homeassistant.util.async import run_coroutine_threadsafe
except:
    from homeassistant.util.async_ import run_coroutine_threadsafe
from homeassistant.components.http import HomeAssistantView
from homeassistant.components.http import setup_cors
import homeassistant.helpers.config_validation as cv

#from .redpoint_agent import redpoint_agent

DOMAIN = 'redpoint'

_LOGGER = logging.getLogger(__name__)
CONF_STARTUP_CMD = 'hass_cmd'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional(CONF_STARTUP_CMD): cv.string
        }),
}, extra=vol.ALLOW_EXTRA)


def setup(hass, config=None):
    """Set up the component."""

    if config[DOMAIN].get(CONF_STARTUP_CMD):
        startup_cmd = config[DOMAIN].get(CONF_STARTUP_CMD)
    else:
        startup_cmd = sys.argv[0]

    rpa = redpoint_agent(ConfigPath=hass.config.config_dir, Cmd_hass=startup_cmd)
    rpa.copyConfig()

    token = '/%s'%(str(uuid.uuid4()))

    views={
        "Redpoint:root":["/redpoint", True, RedpointRootView],
        "Redpoint:redirect":["%s/redpoint/redirect"%(token), False, RedpointRedirectView],
        "Redpoint:check":["%s/redpoint/check"%(token), False, RedpointCheckView],
        "Redpoint:configuration":["%s/redpoint/configuration"%(token), False, RedpointConfigurationView],
        "Redpoint:info":["%s/redpoint/info"%(token), False, RedpointInfoView],
        "Redpoint:version":["%s/redpoint/version"%(token), False, RedpointVersionView],
        "Redpoint:publish":["%s/redpoint/publish"%(token), False, RedpointPublishView],
        "Redpoint:restart":["%s/redpoint/restart"%(token), False, RedpointRestartView],
        "Redpoint:sourcecode":["%s/redpoint/sourcecode"%(token), False, RedpointSourcecodeView],
        }
    for name, t in views.items():
        view = t[2]()
        setattr( view, 'name', name )
        setattr( view, 'url', t[0] )
        setattr( view, 'requires_auth', t[1] )
        setattr( view, 'rpa', rpa )
        setattr( view, 'token', token )
        setattr( view, 'hass', hass )

        hass.http.register_view(view)

    if not "cors_allowed_origins" in config["http"]:
        setup_cors(hass.http.app, ["http://redpoint.hachina.io"])

    #yield from hass.components.frontend.async_register_built_in_panel(
    #    'iframe', "红点", "mdi:hand-pointing-right",
    #    'redpoint_config', {'url': views["Redpoint:redirect"][0]})
    run_coroutine_threadsafe(hass.components.frontend.async_register_built_in_panel(
                           'iframe', "红点", "mdi:hand-pointing-right",
                           'redpoint_config', {'url': views["Redpoint:redirect"][0]}),
                             hass.loop
                       )
    return True

class RedpointRootView(HomeAssistantView):
    """View to return defined themes."""
    @asyncio.coroutine
    def get(self, request):
        """Return themes."""
        msg = "<script>window.location.assign(\"http://redpoint.hachina.io/haconfig?agent=%s%s\");</script>"%(str(request.url.origin()), self.token)
        return web.Response(text=msg, content_type="text/html")

class RedpointRedirectView(HomeAssistantView):
    """View to return defined themes."""
    @asyncio.coroutine
    def get(self, request):
        """Return themes."""
        msg = "<script>window.location.assign(\"http://redpoint.hachina.io/haconfig?agent=%s%s\");</script>"%(str(request.url.origin()), self.token)
        return web.Response(text=msg, content_type="text/html")


class RedpointCheckView(HomeAssistantView):
    """View to return defined themes."""
    @asyncio.coroutine
    def get(self, request):
        """Return themes."""
        #out = self.rpa.Check()
        out = yield from self.hass.async_add_job(self.rpa.Check)
        return web.Response(text=out, content_type="application/json")


class RedpointConfigurationView(HomeAssistantView):
    """View to return defined themes."""
    @asyncio.coroutine
    def get(self, request):
        """Return themes."""
        out = yield from self.hass.async_add_job(self.rpa.ReadConfiguration)
        return web.Response(text=out, content_type="text/plain")

    @asyncio.coroutine
    def post(self, request):
        """Return themes."""
        content= yield from request.json()

        result = yield from self.hass.async_add_job(self.rpa.WriteConfiguration, content['data'])
        if result:
            out = 'OK'
        else:
            out = 'KO'
        return web.Response(text=out, content_type="text/plain")


class RedpointInfoView(HomeAssistantView):
    """View to return defined themes."""
    @asyncio.coroutine
    def get(self, request):
        """Return themes."""
        out = json.dumps(self.rpa.config)
        return web.Response(text=out, content_type="application/json")

class RedpointVersionView(HomeAssistantView):
    """View to return defined themes."""
    @asyncio.coroutine
    def get(self, request):
        """Return themes."""
        out = self.rpa.version
        return web.Response(text=out, content_type="text/plain")


class RedpointPublishView(HomeAssistantView):
    """View to return defined themes."""
    @asyncio.coroutine
    def post(self, request):
        """Return themes."""
        result = yield from self.hass.async_add_job(self.rpa.Publish)
        if result:
            out = 'OK'
        else:
            out = 'KO'
        return web.Response(text=out, content_type="text/plain")

class RedpointRestartView(HomeAssistantView):
    """View to return defined themes."""
    @asyncio.coroutine
    def post(self, request):
        """Return themes."""
        result = yield from self.hass.services.async_call('homeassistant','restart')
        if result:
            out = 'OK'
        else:
            out = 'KO'
        return web.Response(text=out, content_type="text/plain")

class RedpointSourcecodeView(HomeAssistantView):
    """View to return defined themes."""
    @asyncio.coroutine
    def get(self, request):
        """Return themes."""
        comp_name = request.query['component']
        potential_paths = ['custom_components.{}'.format(comp_name),
                           'homeassistant.components.{}'.format(comp_name)]

        ret={}
        for path in potential_paths:
            complib = importlib.util.find_spec(path)
            if complib:
                _LOGGER.info("file = %s", complib.origin)

                f = open(complib.origin,'r', encoding='utf-8')
                ret['fileContent'] = f.read()
                f.close()

                ret['isOK'] = True
                ret['filePath'] = complib.origin
                return web.Response(text=json.dumps(ret), content_type="application/json")

        ret['isOK'] = False
        return web.Response(text=json.dumps(ret), content_type="application/json")
        
