import json, ssl, base64, math, colorsys, logging, re
from urllib.request import urlopen, Request
from AlexaSmartHome import *

_LOGGER = logging.getLogger(__name__)
ENDPOINT_ADAPTERS = Registry()

# ======================================================
# Base Endpoint
# ======================================================

class DomoticzEndpoint(AlexaEndpoint):
    def __init__(self, *args):
        super().__init__(*args)
        self.handler = None
        self._device = None

    def setHandler(self, handler):
        self.handler = handler

    def getDevice(self):
        if not self._device and self.handler:
            self._device = self.handler.getDevice(self.endpointId())
        return self._device

    # ---------------- Alexa Properties ----------------

    def getProperty(self, name):
        d = self.getDevice()
        if not d:
            return None

        if name == 'powerState':
            status = d.get('Status', 'Off')
            return 'ON' if (status in ('On', 'Open') or status.startswith('Set Level')) else 'OFF'

        if name == 'color':
            color_json = d.get('Color', '{}')
            try:
                c = json.loads(color_json)
                r, g, b = c.get('r', 0), c.get('g', 0), c.get('b', 0)
                h, s, v = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
                return {'hue': h*360.0, 'saturation': s, 'brightness': v}
            except Exception:
                # Fallback if color parsing fails
                return None

        if name in ('brightness', 'percentage'):
            return int(d.get('Level', 0))

        if name == 'temperature':
            t = d.get('Temp')
            if t is None:
                return None
            return {'value': float(t), 'scale': 'CELSIUS'}

        if name == 'targetSetpoint':
            sp = d.get('SetPoint')
            if sp is None:
                return None
            return {'value': float(sp), 'scale': 'CELSIUS'}

        if name == 'thermostatMode':
            names = d.get('LevelNames', '').split('|')
            try:
                idx = int(d.get('Level', 0) / d.get('LevelInt', 10))
                return names[idx].upper()
            except Exception:
                return 'AUTO'

        if name == 'detectionState':
            return 'DETECTED' if d.get('Status') == 'Open' else 'NOT_DETECTED'

        return None


# ======================================================
# Endpoints
# ======================================================

@ENDPOINT_ADAPTERS.register('SwitchLight')
class SwitchLightEndpoint(DomoticzEndpoint):
    def __init__(self, *args):
        super().__init__(*args)
        self.addCapability(AlexaPowerController(self))
        self.addCapability(AlexaBrightnessController(self))

    def turnOn(self):
        self.handler.setSwitch(self.idx, 'On')

    def turnOff(self):
        self.handler.setSwitch(self.idx, 'Off')

    def setBrightness(self, value):
        self.handler.setLevel(self.idx, value)

    def setColor(self, h, s, b):
        r, g, b_val = [int(x*255) for x in colorsys.hsv_to_rgb(h/360.0, s, b/100.0)]
        self.handler.setColor(self.idx, r, g, b_val)

    def setColorTemperature(self, kelvin):
        self.handler.setColorTemperature(self.idx, kelvin)


@ENDPOINT_ADAPTERS.register('Blind')
class BlindEndpoint(DomoticzEndpoint):
    def __init__(self, *args):
        super().__init__(*args)
        self.addCapability(AlexaPowerController(self))
        self.addCapability(AlexaPercentageController(self))

    def turnOn(self):
        self.handler.setSwitch(self.idx, 'Off')

    def turnOff(self):
        self.handler.setSwitch(self.idx, 'On')

    def setPercentage(self, value):
        self.handler.setLevel(self.idx, value)


@ENDPOINT_ADAPTERS.register('TemperatureSensor')
class TemperatureSensorEndpoint(DomoticzEndpoint):
    def __init__(self, *args):
        super().__init__(*args)
        self.addCapability(AlexaTemperatureSensor(self))
        self.addDisplayCategories("TEMPERATURE_SENSOR")


@ENDPOINT_ADAPTERS.register('Thermostat')
class ThermostatEndpoint(DomoticzEndpoint):
    def __init__(self, *args):
        super().__init__(*args)
        self.addCapability(AlexaTemperatureSensor(self))
        tc = AlexaThermostatController(
            self,
            properties=[{'name': 'targetSetpoint'}, {'name': 'thermostatMode'}]
        )
        tc.setModesSupported(['HEAT', 'COOL', 'AUTO', 'OFF'])
        self.addCapability(tc)
        self.addDisplayCategories("THERMOSTAT")

    def setTargetSetPoint(self, value):
        self.handler.setSetpoint(self.idx, value)

    def setThermostatMode(self, mode):
        self.handler.setLevelByName(self.idx, mode)


@ENDPOINT_ADAPTERS.register('Scene')
class SceneEndpoint(DomoticzEndpoint):
    def __init__(self, *args):
        super().__init__(*args)
        self.addCapability(AlexaSceneController(self))
        self.addDisplayCategories("SCENE")

    def activate(self):
        self.handler.setScene(self.idx, 'On')

    def deactivate(self):
        self.handler.setScene(self.idx, 'Off')


# ======================================================
# Domoticz Handler
# ======================================================

class Domoticz:
    def __init__(self, url, username=None, password=None):
        self.url = url.rstrip('/')
        self.auth = None
        self.devices = {}
        self.config = None

        if username:
            token = base64.b64encode(f"{username}:{password}".encode()).decode()
            self.auth = f"Basic {token}"

        if self.url.startswith("https"):
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            ssl._create_default_https_context = lambda: ctx

    def configure(self, config):
        self.config = config

    # ---------------- API ----------------

    def api(self, query):
        url = f"{self.url}/json.htm?{query}"
        headers = {'Content-Type': 'application/json'}
        if self.auth:
            headers['Authorization'] = self.auth

        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=5) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            _LOGGER.error(f"Domoticz API error: {e}")
            return {}

    # ---------------- Load ----------------

    def loadDevices(self):
        res = self.api("type=command&param=getdevices&filter=all&used=true")
        self.devices = {str(d['idx']): d for d in res.get('result', [])}

        if self.config and getattr(self.config, 'includeScenesGroups', False):
            res = self.api("type=command&param=getscenes")
            for d in res.get('result', []):
                self.devices[str(d['idx'])] = d

    # ---------------- Alexa ----------------

    def getEndpoint(self, request):
        """
        Called by AlexaSmartHome for EVERY directive
        (TurnOn, TurnOff, SetBrightness, etc.)
        """
        endpointId = request['endpoint']['endpointId']
        prefix, idx = endpointId.split("-", 1)

        if prefix not in ENDPOINT_ADAPTERS:
            raise Exception(f"Unknown endpoint type {prefix}")

        # Create endpoint instance dynamically
        endpoint = ENDPOINT_ADAPTERS[prefix](
            endpointId,
            request['endpoint'].get('friendlyName', ''),
            '',
            'Domoticz'
        )

        endpoint.idx = idx
        endpoint.setHandler(self)

        # Attach cached device
        device = self.devices.get(idx)
        if device:
            endpoint._device = device

        return endpoint

    def getDevice(self, endpointId):
        parts = endpointId.split("-")
        idx = parts[-1]
        
        # Return cached if available
        if idx in self.devices:
            return self.devices[idx]

        # Not in cache? Fetch it from Domoticz
        prefix = parts[0]
        if prefix == 'Scene':
            res = self.api("type=command&param=getscenes")
            for d in res.get('result', []):
                self.devices[str(d['idx'])] = d
        else:
            res = self.api(f"type=command&param=getdevices&rid={idx}")
            if res.get('result'):
                self.devices[idx] = res['result'][0]
        
        return self.devices.get(idx)

    def getEndpoints(self):
        self.loadDevices()
        eps = []

        for idx, d in self.devices.items():
            name = d.get('Name', f"Device {idx}")
            desc = d.get('Description', '')
            if desc:
                match = re.search(r'Alexa_Name:\s*([^\n\r]*)', desc, re.IGNORECASE)
                if match:
                    name = match.group(1).strip()
            devType = d.get('Type', '')

            if devType in ('Scene', 'Group'):
                ep = SceneEndpoint(f"Scene-{idx}", name, devType, "Domoticz")

            elif 'Temp' in devType:
                ep = TemperatureSensorEndpoint(
                    f"TemperatureSensor-{idx}", name, devType, "Domoticz"
                )

            elif 'Thermostat' in devType:
                ep = ThermostatEndpoint(
                    f"Thermostat-{idx}", name, devType, "Domoticz"
                )

            elif 'Blind' in devType or 'RFY' in devType:
                ep = BlindEndpoint(
                    f"Blind-{idx}", name, devType, "Domoticz"
                )

            else:
                ep = SwitchLightEndpoint(
                    f"SwitchLight-{idx}", name, devType, "Domoticz"
                )
                # Add color capabilities if device supports it
                subType = d.get('SubType', '')
                if 'RGB' in subType or 'Color' in devType:
                    ep.addCapability(AlexaColorController(ep))
                    ep.addCapability(AlexaColorTemperatureController(ep))
                ep.addDisplayCategories("LIGHT")

            ep.idx = idx
            ep.setHandler(self)
            eps.append(ep)

        _LOGGER.warning(f"Alexa Discovery endpoints: {len(eps)}")
        return eps

    # ---------------- Actions ----------------

    def setSwitch(self, idx, cmd):
        self.api(f"type=command&param=switchlight&idx={idx}&switchcmd={cmd}")

    def setLevel(self, idx, level):
        self.api(
            f"type=command&param=switchlight&idx={idx}&switchcmd=Set%20Level&level={level}"
        )

    def setColor(self, idx, r, g, b):
        self.api(f"type=command&param=setcolbrightnessvalue&idx={idx}&r={r}&g={g}&b={b}&brightness=100")

    def setColorTemperature(self, idx, kelvin):
        # Map Kelvin (2000-6500) to Domoticz level (0-100)
        level = int((kelvin - 2000) / (6500 - 2000) * 100)
        level = max(0, min(100, level))
        self.api(f"type=command&param=setcolbrightnessvalue&idx={idx}&color={{\"m\":3,\"t\":{level}}}")

    def setSetpoint(self, idx, value):
        self.api(
            f"type=command&param=setsetpoint&idx={idx}&setpoint={value}"
        )

    def setLevelByName(self, idx, name):
        d = self.devices.get(str(idx))
        names = d.get('LevelNames', '').split('|')
        if name.upper() in [n.upper() for n in names]:
            lvl = names.index(name.upper()) * d.get('LevelInt', 10)
            self.setLevel(idx, lvl)

    def setScene(self, idx, cmd):
        self.api(
            f"type=command&param=switchscene&idx={idx}&switchcmd={cmd}"
        )
