import abc
import logging
import sys

from datetime import datetime
from typing import List
from slack_sdk import WebClient as SlackClient
from twilio.rest import Client as TwilioClient
from varname import nameof

class SenderBase(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def send_message(self, message: str): 
        pass

    @abc.abstractmethod
    def schedule_message(self, message: str, send_at: datetime):
        pass

    @classmethod
    def sender_name(self) -> str:
        return __class__.__name__.replace("_", " ").title()

    @classmethod
    def validate_not_empty(self, action: str, val, valName: str):
        if not val:
            logging.error(f'Error {action}: {valName} can not be emoty.')
            sys.exit()


class Slack(SenderBase):
    def __init__(self, access_token: str, recipients: List[str]):
        action = f'initializing instance of {__class__.__name__ }'

        self.validate_not_empty(action, recipients, nameof(recipients))
        self.validate_not_empty(action, access_token, nameof(access_token))
        
        self._recipients = recipients
        self._client = SlackClient(token=access_token)

    @property
    def client(self):
        return self._client

    @property
    def recipients(self):
        return self._recipients

    def send_message(self, message: str):
        messages = []
        for recipient in self.recipients:
            messages.append( \
                self.client \
                    .chat_postMessage(
                        channel=recipient, 
                        text=message
                    ))
        return messages

    def schedule_message(self, message: str, send_at: datetime):
        messages = []
        for recipient in self.recipients:
            messages.append( \
                self.client \
                    .chat_scheduleMessage(
                        channel=recipient,
                        text=message,
                        post_at=send_at.timestamp()
                    ))
        return messages

class Twilio_Sms(SenderBase):
    def __init__(self, auth_token: str, account_sid: str, messaging_service_sid: str, recipients: List[str]):
        action = f'Initializing instance of {__class__.__name__ }'
        
        self.validate_not_empty(action, auth_token, nameof(auth_token))
        self.validate_not_empty(action, account_sid, nameof(account_sid))
        self.validate_not_empty(action, messaging_service_sid, nameof(messaging_service_sid))

        self._recipients = recipients
        self._messaging_service_sid = messaging_service_sid
        self._client = TwilioClient(account_sid, auth_token)

    @property
    def client(self):
        return self._client

    @property
    def messaging_service_sid(self):
        return self._messaging_service_sid

    @property
    def recipients(self):
        return self._recipients

    def send_message(self, message: str):
        messages = []
        for recipient in self.recipients:
            message = self.client.messages \
                .create(
                     body=message,
                     from_=self.messaging_service_sid,
                     to=recipient
                 )
                 
            messages.append(message)
                
        return messages

    def schedule_message(self, message: str, send_at: datetime):
        messages = []
        for recipient in self.recipients:
            message = self.client.messages \
                .create(
                        from_=self.messaging_service_sid,
                        to=recipient,
                        body=message,
                        schedule_type='fixed',
                        send_at=send_at.isoformat() + 'Z'
                )
                
            messages.append(message)
        return messages