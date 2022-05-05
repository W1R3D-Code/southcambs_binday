import logging
import dateutil.parser
import pytz

from .senders import *

from datetime import time, timezone
from os import environ
from typing import Type

class AppConfig():
    def __init__(self):
        self._senders = []
        self.notification_preferences = NotificationPreferences()
        self.slack = SlackConfig()
        self.twilio_sms = TwilioSmsConfig()
        self.waste_collection = WasteCollectionConfig()

    def is_valid(self) -> bool:
        errors = []
        if not self.notification_preferences.configured:
            errors.append('Invalid or missing notification preferences')

        if not self.waste_collection.configured:
            errors.append('Invalid or missing waste collection api config')

        if not self.senders:
            errors.append('Invalid or missing message senders configured.')

        if errors:
            config_errors = ', '.join(errors)
            logging.error(f'Config errors: {config_errors}')
            return False

        return True

    @property
    def senders(self) -> list:
        if self._senders:
            return self._senders
        else:
            self._senders = []

        if self.slack.configured:
            self._senders.append(self.slack.get_sender())

        if self.twilio_sms.configured:
            self._senders.append(self.twilio_sms.get_sender())

        return self._senders

class NotificationPreferences():
    def __init__(self):
        try:
            self.configured = False

            # Defaults
            self.timezone = datetime.now(pytz.utc).astimezone().tzinfo #local timezone
            self.configured = True # valid with only defaults

            if 'timezone' in environ:
                self.timezone = pytz.timezone(environ['timezone'])

        except Exception as e:     
            logging.warn('Error parsing notification preferences config: ' + str(e))

    def parse_bool(self, value: str) -> bool:
        return value.lower() in ('yes', 'true', 'y', 't', '1')
            
class SlackConfig():
    def __init__(self):
        try:
            self.configured = False
            self.access_token = environ['slack_access_token']
            self.recipients = environ['slack_recipients'].split(',')
            self.configured = True
        except Exception as e:     
            logging.warn('Error parsing slack config: ' + str(e))

    def get_sender(self) -> Type[SenderBase]:
        if self.configured:
            return Slack(self.access_token, self.recipients)
        else:
            return None

class TwilioSmsConfig():
    def __init__(self):
        try:
            self.configured = False
            self.account_sid = environ['twilio_account_sid']
            self.auth_token = environ['twilio_auth_token']
            self.messageing_service_sid = environ['twilio_messageing_service_sid']
            self.recipients = environ['twilio_recipients'].split(',')
            self.configured = True
        except Exception as e:     
            logging.warn(f'Error parsing twilio config: {str(e)}')

    def get_sender(self) -> Type[SenderBase]:
        if self.configured:
            return Twilio_Sms(self.auth_token, self.account_sid, self.messageing_service_sid, self.recipients)
        else:
            return None

class WasteCollectionConfig():
    def __init__(self):        
        try:
            self.configured = False
            self.api_base_url = environ['waste_api_url']
            self.postcode = environ['postcode']
            self.house_number = environ['house_number']

            if self.api_base_url and self.postcode and self.house_number:
                self.configured = True
        except Exception as e:     
            logging.warn(f'Error parsing waste collection api config: {str(e)}')