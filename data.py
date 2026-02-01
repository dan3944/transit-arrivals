import datetime as dt
from google.transit import gtfs_realtime_pb2
from dataclasses import dataclass


@dataclass(init=False)
class Arrival:
    route_id: str
    stop_id: str
    direction: str
    when: dt.datetime

    def __init__(self, event: gtfs_realtime_pb2.TripUpdate.StopTimeUpdate, route_id: str):
        if not event.stop_id:
            raise Exception(f'Arrival() missing stop_id from event: {event}')
        self.route_id = route_id
        self.stop_id = event.stop_id[:-1]
        self.direction = event.stop_id[-1]
        self.when = dt.datetime.fromtimestamp(event.arrival.time)

    def wait_minutes(self, now: dt.datetime) -> int:
        wait_time = self.when - now
        return wait_time.seconds // 60 + wait_time.days * 24 * 60
