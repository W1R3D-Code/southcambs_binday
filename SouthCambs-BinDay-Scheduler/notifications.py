import operator
import pytz

from .events import WasteCollection

from collections import defaultdict, OrderedDict
from datetime import datetime, timedelta, timezone
from itertools import groupby
from typing import Callable, List

class Notification():
    def __init__(self, message: str, send_at_utc: datetime = None):
        if not message:
            raise ValueError('message is required')

        self._message = message
        self._send_at_utc = send_at_utc.astimezone(pytz.utc) if send_at_utc else None

    @property
    def message(self) -> str:
        return self._message

    @property
    def send_at_utc(self) -> datetime:
        return self._send_at_utc

    def is_scheduled(self) -> bool:
        return self.send_at_utc is not None and self.send_at_utc > datetime.now()

class NotificationConfig:
    def __init__(
                 self,
                 name: str,
                 template: str = '{{GROUP_MESSAGE}}',
                 grouped_event_template: str = '{{BIN_NAMES}} {{BIN_TYPE}} collection on {{COLLECTION_DAY}} {{COLLECTION_DATE}}',
                 timezone: timezone = pytz.utc,
                 event_range: timedelta = timedelta(days=1),
                 notification_days: List[str] = None,
                 operator: str = '=',
                ) -> None:

        self._name = name
        self._notification_template = template.strip()
        self._group_template = grouped_event_template.strip()
        self._timezone = timezone
        self._event_range = event_range
                
        self._notification_days = (
            None if not notification_days 
                or any(x.lower() in ['any', 'all', '*'] for x in notification_days) 
            else [self.__parse_day(d) for d in notification_days])

        self._operator = self.__parse_operator(operator)

    @property
    def name(self) -> str:
        return self._name

    @property
    def notification_template(self) -> str:
        return self._notification_template

    @property
    def group_template(self) -> str:
        return self._group_template

    @property
    def event_range(self) -> timedelta:
        return self._event_range

    @property
    def notification_days(self) -> List[int]:
        return self._notification_days

    @property
    def timezone(self) -> timezone:
        return self._timezone

    @property
    def operator(self) -> operator:
        return self._operator

    def get_relevant(self, events: List[WasteCollection], operator: operator = None) -> List[object]:
        return list(self.__filter(events, operator))

    def get_notifications(self, events: List[WasteCollection]) -> List[Notification]:
        notifications = []

        relevant_events = self.get_relevant(events, self.operator)
        
        # TODO:: add notification times param to allow for scheduled notifications
        if relevant_events:
            notifications.append(
                Notification(self.__generate_notification_message(
                    self.notification_template, self.group_template, relevant_events
                    )
                )
            )
        
        return notifications

    def __event_range_max_date(self) -> datetime:
        return (datetime.now(self.timezone) + self.event_range).date()

    def __is_valid_notification_day(self) -> bool:
        return (not self.notification_days 
                or datetime.now(self.timezone).date().weekday() in self.notification_days)

    def __filter(self, events: List[WasteCollection], operator: operator = None) -> filter:
        func: Callable[[WasteCollection], bool] = (
            lambda x: self.__is_valid_notification_day() 
                and operator(
                    self.__event_range_max_date(),
                    x.date(self.timezone)
                )
            )            
        return filter(func, events)

    def __parse_day(self, value: str) -> int:
        value = value.lower()
        if value == 'monday' or value == 'mon':
            return 0
        elif value == 'tuesday' or value == 'tue':
            return 1
        elif value == 'wednesday' or value == 'wed':
            return 2
        elif value == 'thursday' or value == 'thu':
            return 3
        elif value == 'friday' or value == 'fri':
            return 4
        elif value == 'saturday' or value == 'sat':
            return 5
        elif value == 'sunday' or value == 'sun':
            return 6
        else:
            raise ValueError(f'Day {value} not supported.')

    def __parse_operator(self, value: str) -> operator:
        if value == '=':
            return operator.eq
        if value == '!=':
            return operator.ne
        elif value == '<':
            return operator.lt
        elif value == '<=':
            return operator.le
        elif value == '>':
            return operator.gt
        elif value == '>=':
            return operator.ge
        else:
            raise ValueError(f'Operator {value} not supported.')

    def __generate_notification_message(self, template: str, group_template: str, events: List[WasteCollection]) -> str:
        group_func: Callable[[WasteCollection], datetime] = lambda x: x.collection_date_utc.date()
        sorted_events = sorted(events, key=group_func)
        grouped_events = [list(results) for key, results in groupby(sorted_events, group_func)]
        
        group_messages = []
        for event_group in grouped_events:
            binTypes = defaultdict(list)
            for collection in event_group:
                binTypes[collection.bin_type].append(collection.bin_name.title())
                binTypes[collection.bin_type].sort()

            binTypes = OrderedDict(sorted(binTypes.items()))
            for binType in binTypes:
                group_messages.append(
                    self.__replace_collection_placeholders(
                        group_template
                        .replace('{{BIN_NAMES}}', f'{" & ".join(binTypes[binType])}')
                        .replace('{{BIN_TYPE}}', binType)
                        .replace('{{COLLECTION_DAY}}', event_group[0].day_name(self.timezone))
                        .replace('{{COLLECTION_DATE}}', self.__date_with_suffix(event_group[0].day(self.timezone)))
                        .replace('{{COLLECTION_SUM}}', str(len(events)))
                        )
                    )

        for index, message in enumerate(group_messages):
            group_messages[index] = self.__replace_collection_placeholders(message)

        group_message = '\n'.join(group_messages)
        return self.__replace_collection_placeholders(template).replace('{{GROUP_MESSAGE}}', group_message)

    def __replace_collection_placeholders(self, message: str) -> str:
        return (
            message
            .replace('{{NOTIFICATION_NAME}}', self.name)
            .replace('{{TIMESTAMP}}', datetime.now(self.timezone).strftime('%H:%M:%S'))
            .replace('{{DATE_SHORT}}', datetime.now(self.timezone).strftime('%m/%d/%Y'))
            .replace('{{DATE_LONG}}', datetime.now(self.timezone).strftime('%m/%d/%Y %H:%M:%S'))
        )

    def __date_with_suffix(self, date: int) -> str:
        return f'{str(date)}{("th" if 11 <= date <= 13 else { 1:"st", 2:"nd", 3:"rd" }.get(date % 10, "th"))}'