import os
import sys
import datetime
import logging
import pip._vendor.requests as requests
import dateutil.parser
import azure.functions as func

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    if mytimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function ran at %s', utc_timestamp)

    # WASTE COLLECTION API CONFIG
    apiBaseUrl = os.environ["ApiBaseUrl"]
    postcode = os.environ["Postcode"]
    houseNumber = os.environ["HouseNumber"]

    # REMINDER PREFERENCES
    remind_immediately = False
    
    # Default values
    day_before_reminder_time = datetime.time(hour=20, minute=30)
    day_of_reminder_time = datetime.time(hour=7, minute=30)

    try:
        remind_immediately = parse_bool(os.environ["ImmediateReminder"])
        day_before_reminder_time = dateutil.parser.parse(os.environ["DayBeforeReminderTime"]).time()
        day_of_reminder_time = dateutil.parser.parse(os.environ["DayofReminderTime"]).time()
    except Exception as e:
        logging.error('invalid config: '+ str(e))

    # SLACK CONFIG
    slack_token = os.environ["SLACK_ACCESS_TOKEN"]
    user_id = os.environ["SLACK_USER_ID"]

    messages = []
    scheduled_messages = []
    collections = get_collections(apiBaseUrl, postcode, houseNumber)
    
    tomorrow_date = (datetime.datetime.today() + datetime.timedelta(days=1)).date()    
    
    collections = distinct([
                    replace_placeholders(roundType)
                    for c in collections 
                    for roundType in c['roundTypes'] 
                    if dateutil.parser.isoparse(c["date"]).date() == tomorrow_date
                ])

    collections.sort()
    collection_text = ' & '.join(collections) + ' bin day'

    if collections:
        # TODO: check for existing matching messages before adding
        if remind_immediately:
            messages.append(collection_text + ' tomorrow')

        # TODO: check for existing matching scheduled messages before adding
        scheduled_messages.append({
            'text': collection_text + ' tomorrow',
            'post_at': datetime.datetime.combine(datetime.datetime.today(), day_before_reminder_time).timestamp()
            })
        scheduled_messages.append({
            'text': collection_text + ' today!',
            'post_at': datetime.datetime.combine(tomorrow_date, day_of_reminder_time).timestamp()
            })
    
    try:
        for message in messages:
            slack_postMessage(slack_token, user_id, message)
            
        for scheduled_message in scheduled_messages:
            slack_postScheduledMessage(slack_token, user_id, scheduled_message['text'], scheduled_message['post_at'])

    except SlackApiError as e:       
        assert e.response["error"]


def slack_postMessage(token, channel_id, message):
    client = WebClient(token=token)
    return client.chat_postMessage(
                channel=channel_id, 
                text=message
            )

def slack_postScheduledMessage(token, channel_id, message, post_at):
    client = WebClient(token=token)
    return client.chat_scheduleMessage(
                channel=channel_id,
                text=message,
                post_at=post_at
            )

def get_collections(apiBaseUrl, postcode, houseNumber):
    addressSearch = requests.get(f'{apiBaseUrl}/address/search?postCode={postcode}')

    if not addressSearch.ok:
        logging.error(f'Address Search returned {addressSearch.status_code}. {addressSearch.reason}')
        sys.exit()

    addresses = addressSearch.json()

    if not addresses:
        logging.error('addresses is null')
        sys.exit()
    
    address = [a for a in addresses if a["houseNumber"] == houseNumber][0]

    if not address:
        logging.error('address is null, can''t find house number ' + houseNumber)
        sys.exit()

    addressId = address["id"]    
    collectionSearch = requests.get(f'{apiBaseUrl}/collection/search/{addressId}?numberOfCollections=2')

    if not collectionSearch.ok:
        logging.error(f'Waste Calendar Search returned{collectionSearch.status_code}. {collectionSearch.reason}')
        sys.exit()

    collections = collectionSearch.json()["collections"]

    if not collections:
        logging.error('No bin collections found')
        sys.exit()

    return collections

def replace_placeholders(message):
    return (
        message
        .replace('DOMESTIC', 'Black')
        .replace('RECYCLE', 'Blue')
        .replace('ORGANIC', 'Green')
    )

def parse_bool(value):
  return value.lower() in ("yes", "true", "y", "t", "1")

def distinct(x):
    return list(set(x))