import sys
import logging
import pytz
import pip._vendor.requests as requests
import dateutil.parser
import azure.functions as func

from .senders import *
from .config import *
from .notifications import Notification, NotificationConfig
from .events import WasteCollection

from datetime import datetime, timedelta, timezone
from slack_sdk.errors import SlackApiError
from twilio.base.exceptions import TwilioRestException
from typing import List
from varname import nameof

def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.utcnow().replace(
        tzinfo=pytz.utc).isoformat()

    if mytimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function ran at %s', utc_timestamp)

    config = AppConfig()

    if not config or not config.is_valid():
        logging.error('Invalid app config.')
        sys.exit()

    collections = get_southcambs_collections(config.waste_collection)

    if not collections:
        logging.error('No future collections found.')
        sys.exit()

    reminders = get_notifications(config.notification_preferences, collections)

    if reminders:
        orchestrate_notifications(config.senders, reminders)
    else:
        logging.info('No reminders to send.')

def orchestrate_notifications(senders: List[SenderBase], notifications: List[Notification]):
    try:
        if not notifications:
            logging.error(f'{nameof(notifications)} can not be null.')
            sys.exit()

        notification: Notification
        for notification in notifications:
            if not notification.is_scheduled():
                logging.info('Sending messages.')
                for sender in senders:
                    logging.info(f'[{sender.name}] Sending messages: {notification.message}')
                    sender.send_message(notification.message)
            else:
                logging.info('Scheduling messages.')
                for sender in senders:
                    logging.info(f"[{sender.name}] scheduling messages: {notification.message} for {notification.send_at_utc.strftime('%m/%d/%Y %H:%M:%S')}")
                    sender.schedule_message(notification.message, notification.send_at_utc)

    except SlackApiError as e:
        logging.error(f'Slack API error: {e.response["error"]}')
        sys.exit()
    except TwilioRestException as e:
        logging.error(f'Twilio API error: {e}')
        sys.exit()
    except Exception as e:
        logging.error(f'Unexpected error: {e}')
        sys.exit()

def get_southcambs_collections(config: WasteCollectionConfig) -> List[WasteCollection]:
    if not config.configured:
        logging.error('Invalid or missing waste collection api config.')
        sys.exit()

    api_base_url = config.api_base_url
    postcode = config.postcode
    house_number = config.house_number

    addressSearch = requests.get(
        f'{api_base_url}/address/search?postCode={postcode}')

    if not addressSearch.ok:
        logging.error(f'Address Search returned {addressSearch.status_code}. {addressSearch.reason}.')
        sys.exit()

    addresses = addressSearch.json()

    if not addresses:
        logging.error(f'No addresses found in postcode: {postcode}')
        sys.exit()

    addresses = [a for a in addresses if a["houseNumber"] == house_number]

    if not addresses:
        logging.error(f'Can''t find address for No. {house_number} in postcode: {postcode}')
        sys.exit()

    address = addresses[0]
    addressId = address["id"]    
    collectionSearch = requests.get(
        f'{config.api_base_url}/collection/search/{addressId}?numberOfCollections=2')

    if not collectionSearch.ok:
        logging.error(f'Waste Calendar Search returned{collectionSearch.status_code}. {collectionSearch.reason}.')
        sys.exit()

    collections_raw = collectionSearch.json()["collections"]

    if not collections_raw:
        logging.error('No bin collections found.')
        sys.exit()

    collections = []
    for collection in collections_raw:
        for roundType in collection["roundTypes"]:
            collections.append(
                WasteCollection(
                    bin_name = roundType,
                    collection_date_utc = dateutil.parser.isoparse(collection["date"]).astimezone(pytz.utc)
                    )
                )

    return collections

def get_notifications(config: NotificationPreferences, collections: List[WasteCollection]) -> List[Notification]:
    
    notification_configs = []

    if not collections:
        logging.warn('No collections found.')
        return None

    notification_configs.append(
        NotificationConfig(
            name = 'Bin Collection fortnightly lookahead',
            template = "{{NOTIFICATION_NAME}}:\n\n{{GROUP_MESSAGE}}",
            timezone=config.timezone,
            event_range = timedelta(days=14),
            notification_days = ['MON'],
            operator = '>='
            )
        )

    notification_configs.append(
        NotificationConfig(
            name = 'Bin Collection Reminder',
            template = "{{GROUP_MESSAGE}}",
            grouped_event_template = "{{BIN_NAMES}} {{BIN_TYPE}} collection tomorrow",
            timezone=config.timezone,
            event_range = timedelta(days=1),
            operator = '='
            )
        )

    notification_configs.append(
        NotificationConfig(
            name = 'Bin Collection Reminder',
            template = "{{GROUP_MESSAGE}}",
            grouped_event_template = "{{BIN_NAMES}} {{BIN_TYPE}} collection today!",
            timezone=config.timezone,
            event_range = timedelta(),
            operator = '='
            )
        )

    notifications = []
    notification_config: NotificationConfig
    for notification_config in notification_configs:
        notifications += notification_config.get_notifications(collections)

    return notifications