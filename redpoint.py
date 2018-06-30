"""

For more details about HAChina,
https://www.hachina.io/
"""
import subprocess
import shutil
import os
import time
import json
import logging
import asyncio
import uuid
import importlib
import sys
from aiohttp import web
import voluptuous as vol
try:
    from homeassistant.util.async import run_coroutine_threadsafe
except ImportError:
    from homeassistant.util.async_ import run_coroutine_threadsafe
from homeassistant.components.http import HomeAssistantView
from homeassistant.components.http import setup_cors
import homeassistant.helpers.config_validation as cv


DOMAIN = 'redpoint'

_LOGGER = logging.getLogger(__name__)
CONF_STARTUP_CMD = 'hass_cmd'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional(CONF_STARTUP_CMD): cv.string
        }),
}, extra=vol.ALLOW_EXTRA)


class RedpointAgent(object):
    """RedpointAgent"""
    def __init__(self, ConfigPath=None, cmd_hass='hass'):
        self._version = '0.2.9'

        if os.name == 'nt':
            self._startupinfo = subprocess.STARTUPINFO()
            self._startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        else:
            self._startupinfo = None

        self._config = {}
        if ConfigPath is None:
            self._config['config_path'] = self._detect_config_path()
        else:
            self._config['config_path'] = ConfigPath

        self.config_file = os.path.join(
            self._config['config_path'], 'configuration.yaml')
        self.tmp_config_file = os.path.join(
            self._config['config_path'], 'configuration.yaml.tmp')

        self._cmd_hass = cmd_hass.split()

        with open(self.config_file, 'r', encoding='utf8') as configuration:
            self._conf_content = configuration.read()

    def _detect_config_path(self):
        data_dir = os.getenv('APPDATA') if os.name == 'nt' \
            else os.path.expanduser('~')
        return os.path.join(data_dir, '.homeassistant')

    def Check(self):
        shutil.copyfile(self.config_file, self.tmp_config_file)
        with open(self.config_file, 'w', encoding='utf8') as configuration:
            configuration.write(self._conf_content)

        cmd = self._cmd_hass + ["--script",
                                "check_config",
                                "-c",
                                self._config['config_path']]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             stdin=subprocess.PIPE,
                             startupinfo=self._startupinfo)
        out, err = p.communicate()

        shutil.copyfile(self.tmp_config_file, self.config_file)

        if err:
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
        return self._conf_content

    def WriteConfiguration(self, content):
        self._conf_content = content
        return True

    def Publish(self):
        file_backup = self.config_file + '.' + \
            time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))
        shutil.copyfile(self.config_file, file_backup)
        with open(self.config_file, 'w', encoding='utf8') as configuration:
            configuration.write(self._conf_content)
        return True

    @property
    def config(self):
        return self._config

    @property
    def version(self):
        return self._version


def setup(hass, config=None):
    """Set up the component."""

    if config[DOMAIN].get(CONF_STARTUP_CMD):
        startup_cmd = config[DOMAIN].get(CONF_STARTUP_CMD)
    else:
        startup_cmd = sys.argv[0]

    rpa = RedpointAgent(
        ConfigPath=hass.config.config_dir, cmd_hass=startup_cmd)

    token = '/%s' % (str(uuid.uuid4()))

    views = {
        "Redpoint:root": ["/redpoint", True, RedpointRootView],
        "Redpoint:redirect": ["%s/redpoint/redirect" % (token), False, RedpointRedirectView],
        "Redpoint:check": ["%s/redpoint/check" % (token), False, RedpointCheckView],
        "Redpoint:configuration": [
            "%s/redpoint/configuration" % (token), False, RedpointConfigurationView],
        "Redpoint:info": ["%s/redpoint/info" % (token), False, RedpointInfoView],
        "Redpoint:version": ["%s/redpoint/version" % (token), False, RedpointVersionView],
        "Redpoint:publish": ["%s/redpoint/publish" % (token), False, RedpointPublishView],
        "Redpoint:restart": ["%s/redpoint/restart" % (token), False, RedpointRestartView],
        "Redpoint:sourcecode": ["%s/redpoint/sourcecode" % (token), False, RedpointSourcecodeView],
        }
    for name, t in views.items():
        view = t[2]()
        setattr(view, 'name', name)
        setattr(view, 'url', t[0])
        setattr(view, 'requires_auth', t[1])
        setattr(view, 'rpa', rpa)
        setattr(view, 'token', token)
        setattr(view, 'hass', hass)

        hass.http.register_view(view)

    if "cors_allowed_origins" not in config["http"]:
        setup_cors(hass.http.app, ["http://redpoint.hachina.io"])

    run_coroutine_threadsafe(
        hass.components.frontend.async_register_built_in_panel(
            'iframe', "红点", "mdi:hand-pointing-right",
            'redpoint_config', {'url': views["Redpoint:redirect"][0]}
            ),
        hass.loop
        )
    return True


class RedpointRootView(HomeAssistantView):
    """View to return defined themes."""
    @asyncio.coroutine
    def get(self, request):
        """Return themes."""
        loc = "http://redpoint.hachina.io/haconfig?agent=%s%s" % (
            str(request.url.origin()), self.token)
        msg = "<script>window.location.assign(\"%s\");</script>" % (loc)
        return web.Response(text=msg, content_type="text/html")


class RedpointRedirectView(HomeAssistantView):
    """View to return defined themes."""
    @asyncio.coroutine
    def get(self, request):
        """Return themes."""
        loc = "http://redpoint.hachina.io/haconfig?agent=%s%s" % (
            str(request.url.origin()), self.token)
        msg = "<script>window.location.assign(\"%s\");</script>" % (loc)
        return web.Response(text=msg, content_type="text/html")


class RedpointCheckView(HomeAssistantView):
    """View to return defined themes."""
    @asyncio.coroutine
    def get(self, request):
        """Return themes."""
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
        content = yield from request.json()

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
        result = yield from self.hass.services.async_call('homeassistant', 'restart')
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

        ret = {}
        for path in potential_paths:
            complib = importlib.util.find_spec(path)
            if complib:
                _LOGGER.info("file = %s", complib.origin)

                f = open(complib.origin, 'r', encoding='utf-8')
                ret['fileContent'] = f.read()
                f.close()

                ret['isOK'] = True
                ret['filePath'] = complib.origin
                return web.Response(text=json.dumps(ret), content_type="application/json")

        ret['isOK'] = False
        return web.Response(text=json.dumps(ret), content_type="application/json")
