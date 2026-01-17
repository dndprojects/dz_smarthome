import logging
import sys, operator

from uuid import uuid4
from datetime import datetime
from typing import Tuple

import math, colorsys
import traceback 
from typing import Callable, TypeVar

CALLABLE_T = TypeVar('CALLABLE_T', bound=Callable)  # noqa pylint: disable=invalid-name

class Registry(dict):
    """Registry of items."""
    def register(self, name: str) -> Callable[[CALLABLE_T], CALLABLE_T]:
        """Return decorator to register item with a specific name."""
        def decorator(func: CALLABLE_T) -> CALLABLE_T:
            """Register decorated function."""
            self[name] = func
            return func

        return decorator

INTERFACES = Registry()

class AlexaInterface:

    # UPDATED: Set proactivelyReported to True by default to enable state updates in Alexa app.
    def __init__(self, endpoint, name = 'Alexa', properties = [], proactivelyReported = True, retrievable = True, modesSupported = None, deactivationSupported = None):
        self._endpoint = endpoint
        self._name = name
        self._properties = properties
        self._proactivelyReported = proactivelyReported
        self._retrievable = retrievable
        self._modesSupported = modesSupported
        self._deactivationSupported = deactivationSupported

    def name(self):
        return self._name

    def version(self):
        return "3"

    def propertiesSupported(self):
        return self._properties

    def propertiesProactivelyReported(self):
        return self._proactivelyReported

    def propertiesRetrievable(self):
        return self._retrievable

    def supportsDeactivation(self):
        return self._deactivationSupported

    def configuration(self):
        return None

    def supportScheduling(self):
        return False

    def modesSupported(self):
        return self._modesSupported

    def setModesSupported(self, modesSupported):
        self._modesSupported = modesSupported

    def serializeDiscovery(self):
        result = {
            'type': 'AlexaInterface',
            'interface': self.name(),
            'version': self.version(),
        }
        props = self.propertiesSupported()
        if props:
            result['properties'] = {
                'supported': props,
                'proactivelyReported': self.propertiesProactivelyReported(),
                'retrievable': self.propertiesRetrievable(),
            }
        if self.configuration() is not None:
            result['configuration'] = self.configuration()
        return result

    def serializeProperties(self):
        for prop in self.propertiesSupported():
            prop_name = prop['name']
            prop_value = self._endpoint.getProperty(prop_name)
            if prop_value is not None:
                yield {
                    'name': prop_name,
                    'namespace': self.name(),
                    'value': prop_value,
                    'timeOfSample': datetime.utcnow().replace(microsecond=0).isoformat()+"Z",
                    'uncertaintyInMilliseconds': 0,
                }

class AlexaEndpoint(object):
    def __init__(self, endpointId, friendlyName="", description="", manufacturerName=""):
        self._endpointId = endpointId
        self._friendlyName = friendlyName
        self._description = description
        self._manufacturerName = manufacturerName
        self._capabilities = [AlexaInterface(self)]
        self._displayCategories = []
        self._cookies = {}

    def endpointId(self):
        return self._endpointId

    def friendlyName(self):
        return self._friendlyName

    def description(self):
        return self._description

    def manufacturerName(self):
        return self._manufacturerName

    def displayCategories(self):
        return self._displayCategories

    def capabilities(self):
        return self._capabilities

    def cookies(self):
        return self._cookies

    def getProperty(self, name):
        return None

    def addDisplayCategories(self, category):
        self._displayCategories.append(category)

    def addCapability(self, interface):
        self._capabilities.append(interface)

    def addCookie(self, dict):
        for k, v in dict.items():
            self._cookies[k] = v

@INTERFACES.register('Alexa.PowerController')
class AlexaPowerController(AlexaInterface):
    def name(self):
        return 'Alexa.PowerController'

    def propertiesSupported(self):
        return [{'name': 'powerState'}]

@INTERFACES.register('Alexa.LockController')
class AlexaLockController(AlexaInterface):
    def name(self):
        return 'Alexa.LockController'

    def propertiesSupported(self):
        return [{'name': 'lockState'}]

@INTERFACES.register('Alexa.SceneController')
class AlexaSceneController(AlexaInterface):
    def name(self):
        return 'Alexa.SceneController'

    def serializeDiscovery(self):
        result = {
            'type': 'AlexaInterface',
            'interface': self.name(),
            'version': self.version(),
            'supportsDeactivation': self.supportsDeactivation(),
        }
        return result

@INTERFACES.register('Alexa.BrightnessController')
class AlexaBrightnessController(AlexaInterface):
    def name(self):
        return 'Alexa.BrightnessController'

    def propertiesSupported(self):
        return [{'name': 'brightness'}]

@INTERFACES.register('Alexa.ColorController')
class AlexaColorController(AlexaInterface):
    def name(self):
        return 'Alexa.ColorController'

    def propertiesSupported(self):
        return [{'name': 'color'}]

@INTERFACES.register('Alexa.ColorTemperatureController')
class AlexaColorTemperatureController(AlexaInterface):
    def name(self):
        return 'Alexa.ColorTemperatureController'

    def propertiesSupported(self):
        return [{'name': 'colorTemperatureInKelvin'}]

@INTERFACES.register('Alexa.PercentageController')
class AlexaPercentageController(AlexaInterface):
    def name(self):
        return 'Alexa.PercentageController'

    def propertiesSupported(self):
        return [{'name': 'percentage'}]

@INTERFACES.register('Alexa.Speaker')
class AlexaSpeaker(AlexaInterface):
    def name(self):
        return 'Alexa.Speaker'

@INTERFACES.register('Alexa.StepSpeaker')
class AlexaStepSpeaker(AlexaInterface):
    def name(self):
        return 'Alexa.StepSpeaker'

@INTERFACES.register('Alexa.PlaybackController')
class AlexaPlaybackController(AlexaInterface):
    def name(self):
        return 'Alexa.PlaybackController'

@INTERFACES.register('Alexa.InputController')
class AlexaInputController(AlexaInterface):
    def name(self):
        return 'Alexa.InputController'

@INTERFACES.register('Alexa.TemperatureSensor')
class AlexaTemperatureSensor(AlexaInterface):
    def name(self):
        return 'Alexa.TemperatureSensor'

    def propertiesSupported(self):
        return [{'name': 'temperature'}]

@INTERFACES.register('Alexa.ThermostatController')
class AlexaThermostatController(AlexaInterface):
    def name(self):
        return 'Alexa.ThermostatController'

    def propertiesSupported(self):
        return [{'name': 'targetSetpoint'}, {'name': 'thermostatMode'}]

    def configuration(self):
        configuration = None
        if self.modesSupported() is not None:
            configuration = {
              'supportsScheduling': self.supportScheduling(),
              'supportedModes': self.modesSupported()
            }
        return configuration

@INTERFACES.register('Alexa.ContactSensor')
class AlexaContactSensor(AlexaInterface):
    def name(self):
        return 'Alexa.ContactSensor'

    def propertiesSupported(self):
        return [{'name': 'detectionState'}]

API_DIRECTIVE = 'directive'
API_ENDPOINT = 'endpoint'
API_EVENT = 'event'
API_CONTEXT = 'context'
API_HEADER = 'header'
API_PAYLOAD = 'payload'

_LOGGER = logging.getLogger(__name__)

def api_message(request,
                name='Response',
                namespace='Alexa',
                payload=None,
                context=None):
    """Create a API formatted response message.
    """
    payload = payload or {}

    response = {
        API_EVENT: {
            API_HEADER: {
                'namespace': namespace,
                'name': name,
                'messageId': str(uuid4()),
                'payloadVersion': '3',
            },
            API_PAYLOAD: payload,
        }
    }

    # If a correlation token exists, add it to header / Need by Async requests
    token = request[API_HEADER].get('correlationToken')
    if token:
        response[API_EVENT][API_HEADER]['correlationToken'] = token

    # Extend event with endpoint object / Need by Async requests
    if API_ENDPOINT in request:
        response[API_EVENT][API_ENDPOINT] = request[API_ENDPOINT].copy()

    if context is not None:
        response[API_CONTEXT] = context

    return response

def api_error(request,
              namespace='Alexa',
              error_type='INTERNAL_ERROR',
              error_message="",
              payload=None):
    """Create a API formatted error response.

    Async friendly.
    """
    payload = payload or {}
    payload['type'] = error_type
    payload['message'] = error_message

    _LOGGER.info("Request %s/%s error %s: %s",
                 request[API_HEADER]['namespace'],
                 request[API_HEADER]['name'],
                 error_type, error_message)

    return api_message(
        request, name='ErrorResponse', namespace=namespace, payload=payload)

def handle_message(handler, message):
    """Handle incoming API messages."""
    # Read head data
    message = message[API_DIRECTIVE]
    namespace = message[API_HEADER]['namespace']
    name = message[API_HEADER]['name']

    return invoke(namespace, name, handler, message)

class AlexaSmartHomeCall(object):
    def __init__(self, namespace, name, handler):
        self.namespace = namespace
        self.name = name
        self.handler = handler

    def invoke(self, name, request):
        try:
            return operator.attrgetter(name)(self)(request)
        except Exception:
            _LOGGER.exception("Error during Alexa skill invocation for %s/%s", self.namespace, self.name)
            return api_error(request, error_type='INTERNAL_ERROR', error_message="An unexpected error occurred while processing your request.")
class Alexa(object):

    class Discovery(AlexaSmartHomeCall):

        def Discover(self, request):
            discovery_endpoints = []
            endpoints = self.handler.getEndpoints()
            for endpoint in endpoints:
                discovery_endpoint = {
                    'endpointId': endpoint.endpointId(),
                    'friendlyName': endpoint.friendlyName(),
                    'description': endpoint.description(),
                    'manufacturerName': endpoint.manufacturerName(),
                    'displayCategories': endpoint.displayCategories(),
                    'additionalApplianceDetails': {},
                }
                discovery_endpoint['capabilities'] = [
                    i.serializeDiscovery() for i in endpoint.capabilities()]
                if not discovery_endpoint['capabilities']:
                    _LOGGER.debug("Not exposing %s because it has no capabilities", endpoint.endpointId())
                    continue
                discovery_endpoints.append(discovery_endpoint)

            _LOGGER.debug("Request %s/%s", request[API_HEADER]['namespace'], request[API_HEADER]['name'])

            return api_message(
                request, name='Discover.Response', namespace='Alexa.Discovery',
                payload={'endpoints': discovery_endpoints})

    class PowerController(AlexaSmartHomeCall):

        def TurnOn(self, request):
            _LOGGER.debug("Request %s/%s", request[API_HEADER]['namespace'], request[API_HEADER]['name'])
            endpoint = self.handler.getEndpoint(request)
            endpoint.turnOn()
            
            # FIX: Return new state in context to prevent "No Response" error
            properties = [{
                'name': 'powerState',
                'namespace': 'Alexa.PowerController',
                'value': 'ON',
                'timeOfSample': datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
                'uncertaintyInMilliseconds': 0
            }]
            return api_message(request, context={'properties': properties})

        def TurnOff(self, request):
            _LOGGER.debug("Request %s/%s", request[API_HEADER]['namespace'], request[API_HEADER]['name'])
            endpoint = self.handler.getEndpoint(request)
            endpoint.turnOff()
            
            # FIX: Return new state in context to prevent "No Response" error
            properties = [{
                'name': 'powerState',
                'namespace': 'Alexa.PowerController',
                'value': 'OFF',
                'timeOfSample': datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
                'uncertaintyInMilliseconds': 0
            }]
            return api_message(request, context={'properties': properties})

    class BrightnessController(AlexaSmartHomeCall):

        def setbrightness(self, request, endpoint, brightness):
            endpoint.setBrightness(brightness)
            properties = [{
                'name': 'brightness',
                'namespace': 'Alexa.BrightnessController',
                "value": brightness,
                'timeOfSample': datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
                'uncertaintyInMilliseconds': 0
            }]
            return api_message(request, context={'properties': properties})

        def SetBrightness(self, request):
            brightness = int(request[API_PAYLOAD]['brightness'])
            _LOGGER.debug("Request %s/%s brightness %d", 
                   request[API_HEADER]['namespace'], request[API_HEADER]['name'],
                   brightness)
            endpoint = self.handler.getEndpoint(request)
            return self.setbrightness(request, endpoint, brightness)

        def AdjustBrightness(self, request):
            brightness_delta = int(request[API_PAYLOAD]['brightnessDelta'])
            _LOGGER.debug("Request %s/%s brightness_delta %d", 
                        request[API_HEADER]['namespace'], request[API_HEADER]['name'],
                        brightness_delta)
            endpoint = self.handler.getEndpoint(request)
            # Use optimistic calculation if possible or fetch current
            current_brightness = endpoint.getProperty('brightness') or 50
            brightness = current_brightness + brightness_delta
            return self.setbrightness(request, endpoint, brightness)

    class ColorController(AlexaSmartHomeCall):

        def SetColor(self, request):
            h = float(request[API_PAYLOAD]['color']['hue'])
            s = float(request[API_PAYLOAD]['color']['saturation'])
            b = float(request[API_PAYLOAD]['color']['brightness'])
            _LOGGER.debug("Request %s/%s", 
                        request[API_HEADER]['namespace'], request[API_HEADER]['name'])
            endpoint = self.handler.getEndpoint(request)
            endpoint.setColor(h,s,b)
            
            properties = [{
                'name': 'color',
                'namespace': 'Alexa.ColorController',
                'value': request[API_PAYLOAD]['color'],
                'timeOfSample': datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
                'uncertaintyInMilliseconds': 0
            }]
            return api_message(request, context={'properties': properties})

    class ColorTemperatureController(AlexaSmartHomeCall):

        def SetColorTemperature(self, request):
            kelvin = int(request[API_PAYLOAD]['colorTemperatureInKelvin'])
            _LOGGER.debug("Request %s/%s kelvin %d", 
                        request[API_HEADER]['namespace'], request[API_HEADER]['name'],
                        kelvin)
            endpoint = self.handler.getEndpoint(request)
            endpoint.setColorTemperature(kelvin)
            
            properties = [{
                'name': 'colorTemperatureInKelvin',
                'namespace': 'Alexa.ColorTemperatureController',
                'value': kelvin,
                'timeOfSample': datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
                'uncertaintyInMilliseconds': 0
            }]
            return api_message(request, context={'properties': properties})

    class SceneController(AlexaSmartHomeCall):

        def Activate(self, request):
            timestamp = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
            payload = {
                'cause': {'type': 'VOICE_INTERACTION'},
                'timestamp': timestamp
            }
            _LOGGER.debug("Request %s/%s", request[API_HEADER]['namespace'], request[API_HEADER]['name'])
            endpoint = self.handler.getEndpoint(request)
            endpoint.activate()
            return api_message(request,
                name='ActivationStarted', namespace='Alexa.SceneController',
                payload=payload)

        def Deactivate(self, request):
            timestamp = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
            payload = {
                'cause': {'type': 'VOICE_INTERACTION'},
                'timestamp': timestamp
            }
            _LOGGER.debug("Request %s/%s", request[API_HEADER]['namespace'], request[API_HEADER]['name'])
            endpoint = self.handler.getEndpoint(request)
            endpoint.deactivate()
            return api_message(request,
                name='DeactivationStarted', namespace='Alexa.SceneController',
                payload=payload)

    class PercentageController(AlexaSmartHomeCall):

        def SetPercentage(self, request):
            percentage = int(request[API_PAYLOAD]['percentage'])
            _LOGGER.debug("Request %s/%s percentage %d", 
                        request[API_HEADER]['namespace'], request[API_HEADER]['name'],
                        percentage)
            endpoint = self.handler.getEndpoint(request)
            if   (percentage < 0):   percentage = 0
            elif (percentage > 100): percentage = 100
            endpoint.setPercentage(percentage)
            
            properties = [{
                'name': 'percentage',
                'namespace': 'Alexa.PercentageController',
                'value': percentage,
                'timeOfSample': datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
                'uncertaintyInMilliseconds': 0
            }]
            return api_message(request, context={'properties': properties})

    class LockController(AlexaSmartHomeCall):

        def Lock(self, request):
            endpoint = self.handler.getEndpoint(request)
            # Trigger actual lock command if endpoint supports it
            if hasattr(endpoint, 'lock'): endpoint.lock()
            
            properties = [{
                'name': 'lockState',
                'namespace': 'Alexa.LockController',
                'value': 'LOCKED',
                'timeOfSample': datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
                'uncertaintyInMilliseconds': 0
            }]
            _LOGGER.debug("Request %s/%s", request[API_HEADER]['namespace'], request[API_HEADER]['name'])
            return api_message(request, context={'properties': properties})

        def Unlock(self, request):
            endpoint = self.handler.getEndpoint(request)
            if hasattr(endpoint, 'unlock'): endpoint.unlock()
            
            properties = [{
                'name': 'lockState',
                'namespace': 'Alexa.LockController',
                'value': 'UNLOCKED',
                'timeOfSample': datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
                'uncertaintyInMilliseconds': 0
            }]
            _LOGGER.debug("Request %s/%s", request[API_HEADER]['namespace'], request[API_HEADER]['name'])
            return api_message(request, context={'properties': properties})

    class ThermostatController(AlexaSmartHomeCall):

        def SetTargetTemperature(self, request):
            tempScale = "CELSIUS"
            payload = request[API_PAYLOAD]
            endpoint = self.handler.getEndpoint(request)
            
            if 'targetSetpoint' in payload:
                temp = temperature_from_object(payload['targetSetpoint'])
                _LOGGER.debug("Request %s/%s targetSetpoint %.2f",
                            request[API_HEADER]['namespace'], request[API_HEADER]['name'], temp)
                endpoint.setTargetSetPoint(temp)

            properties = [{
                'name': 'targetSetpoint',
                'namespace': 'Alexa.ThermostatController',
                "value": {
                    "value": temp,
                    "scale": tempScale
                },
                'timeOfSample': datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
                'uncertaintyInMilliseconds': 0
            }]
            return api_message(request, context={'properties': properties})

        def SetThermostatMode(self, request):
            mode = request[API_PAYLOAD]['thermostatMode']
            mode = mode if isinstance(mode, str) else mode['value']

            _LOGGER.debug("Request %s/%s targetSetpoint mode %s", 
                        request[API_HEADER]['namespace'], request[API_HEADER]['name'], str(mode))

            endpoint = self.handler.getEndpoint(request)
            endpoint.setThermostatMode(mode)
            properties = [{
                'name': 'thermostatMode',
                'namespace': 'Alexa.ThermostatController',
                "value": mode,
                'timeOfSample': datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
                'uncertaintyInMilliseconds': 0
            }]
            return api_message(request, context={'properties': properties})

    class ReportState(AlexaSmartHomeCall):

        def ReportState(self, request):
            properties = []
            endpoint = self.handler.getEndpoint(request)
            if not endpoint or endpoint.getDevice() is None:
                _LOGGER.error("ReportState failed: Could not fetch device state for %s", request['endpoint']['endpointId'])
                return api_error(request, error_type='ENDPOINT_UNREACHABLE', error_message="Could not connect to Domoticz")

            for interface in endpoint.capabilities():
                properties.extend(interface.serializeProperties())

            _LOGGER.debug("Request %s/%s properties %s", 
                        request[API_HEADER]['namespace'], request[API_HEADER]['name'], str(properties))
            return api_message(request,
                name='StateReport',
                context={'properties': properties})

def invoke(namespace, name, handler, request):
    try:
        # Special case report
        if namespace == "Alexa" and name == "ReportState":
            namespace = "Alexa.ReportState"
        class allowed(object):
            Alexa = Alexa
        make_class = operator.attrgetter(namespace)
        obj = make_class(allowed)(namespace, name, handler)
        return obj.invoke(name, request)

    except Exception:
        _LOGGER.exception("Error processing Alexa directive for %s/%s", namespace, name)
        return api_error(request, error_type='INTERNAL_ERROR', error_message="An unexpected error occurred while processing your directive.")

def temperature_from_object(temp_obj):
    """Get temperature from Temperature object in requested unit."""
    temp = float(temp_obj['value'])
    if temp_obj['scale'] == 'FAHRENHEIT':
        temp = (temp - 32.0) / 1.8
    elif temp_obj['scale'] == 'KELVIN':
        temp -= 273.15
    return temp