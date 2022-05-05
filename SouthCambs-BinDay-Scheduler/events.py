from abc import ABCMeta, abstractmethod
from datetime import datetime, timedelta, timezone
import pytz

class EventBase():
    __metaclass__ = ABCMeta

    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod
    def datetime(self, timezone: timezone = pytz.utc) -> datetime:
        pass

    def day(self, timezone: timezone = pytz.utc):
        return self.datetime(timezone).day

    def day_name(self, timezone: timezone = pytz.utc):
        return self.datetime(timezone).strftime('%A')

    def date(self, timezone: timezone = pytz.utc):
        return self.datetime(timezone).date()

    def date_utc(self):
        return self.datetime().date().astimezone(pytz.utc)

    def time(self, timezone: timezone = pytz.utc):
        return self.datetime(timezone).time()

    def timestamp(self, timezone: timezone = pytz.utc):
        return self.datetime(timezone).timestamp()

    def timedelta(self, timezone: timezone = pytz.utc) -> timedelta:
        return self.datetime(timedelta) - datetime.now(timezone)

class WasteCollection(EventBase):
    def __init__(self, collection_date_utc: datetime, bin_name: str, bin_type: str = 'bin'):
        if not collection_date_utc:
            raise ValueError('collection_date_utc is required')

        if not bin_name:
            raise ValueError('bin_name is required')

        self._collection_date_utc = collection_date_utc.astimezone(pytz.utc) if collection_date_utc.tzinfo else collection_date_utc
        self._bin_name = self.__replace_southcambs_bin_types(bin_name).strip()
        self._bin_type = bin_type.strip()

    def description(self) -> str:
        return f'{self.bin_name} {self.bin_type} day'

    def datetime(self, tz: timezone = pytz.utc) -> datetime:
        return self.collection_date_utc if tz == pytz.utc else self.collection_date_utc.astimezone(tz)

    def __replace_southcambs_bin_types(self, message: str) -> str:
        return (
            message.replace('DOMESTIC', 'Black')
                   .replace('RECYCLE', 'Blue')
                   .replace('ORGANIC', 'Green')
                   )

    @property
    def bin_name(self) -> str:
        return self._bin_name

    @property
    def bin_type(self) -> str:
        return self._bin_type

    @property
    def collection_date_utc(self) -> datetime:
        return self._collection_date_utc