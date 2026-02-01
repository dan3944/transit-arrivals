import aiohttp
import argparse
import asyncio
import csv
import gpiod
import gpiodevice
import logging
import threading
from gpiod.line import Bias, Direction, Edge
from google.transit import gtfs_realtime_pb2
from typing import List

from data import Arrival, Route
from display import Display


<<<<<<< HEAD
async def fetch_feed(url: str, session) -> gtfs_realtime_pb2.FeedMessage:
=======
async def _fetch_feed(url: str, session) -> gtfs_realtime_pb2.FeedMessage:
>>>>>>> buttons
    try:
        async with session.get(url=url) as response:
            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(await response.read())
            return feed
    except Exception as e:
        logging.error(f'Exception when fetching from {url}: {e}')
        return gtfs_realtime_pb2.FeedMessage()

class Controller:
    def __init__(self, stop_ids: List[str], refresh_rate: int) -> None:
        if not (1 <= len(stop_ids) <= 4):
            raise Exception(f'stop_ids must have length between 1 and 4 inclusive (got {len(stop_ids)})')

        self._stop_ids = stop_ids
        self._refresh_rate = refresh_rate
        with open('gtfs_subway/routes.txt') as f:
            self._routes_by_id = {
                line['route_id']: Route(
                    id=line['route_id'],
                    color='#' + line.get('route_color', 'ffffff'),
                    text_color='#' + line.get('route_text_color', '000000'),
                )
                for line in csv.DictReader(f)
            }
        with open('gtfs_subway/stops.txt') as f:
            self._stop_id_to_name = {
                line['stop_id']: line['stop_name']
                for line in csv.DictReader(f)
            }

    def stop_name(self, stop_id: str) -> str:
        return self._stop_id_to_name.get(stop_id, stop_id)

    def run(self):
        chip = gpiodevice.find_chip_by_platform()
        offset_to_stop_id = {
            chip.line_offset_from_id(button): stop_id
            for button, stop_id in zip([5, 6, 16, 24], self._stop_ids)
        }
        request = chip.request_lines(consumer='spectra6-buttons', config={
            offset: gpiod.LineSettings(direction=Direction.INPUT, bias=Bias.PULL_UP, edge_detection=Edge.FALLING)
            for offset in offset_to_stop_id
        })
        current_stop_id = self._stop_ids[0]
        thread, cancel = self._show_station_in_thread(current_stop_id)

        while True:
            for event in request.read_edge_events():
                new_stop_id = offset_to_stop_id.get(event.line_offset)
                if new_stop_id == current_stop_id:
                    continue

                if new_stop_id is None:
                    logging.error(f'Offset "{event.line_offset}" not found in {offset_to_stop_id}')
                    continue

                logging.info(f'Showing stop {self.stop_name(new_stop_id)} (stop_id: {new_stop_id})')
                current_stop_id = new_stop_id
                cancel.set()
                thread.join()
                thread, cancel = self._show_station_in_thread(current_stop_id)

    def _show_station_in_thread(self, stop_id: str) -> tuple[threading.Thread, threading.Event]:
        # We need to run _show_station() in a separate thread because read_edge_events()
        # is blocking, so it will never yield the asyncio loop to other tasks.
        cancel_event = threading.Event()
        thread = threading.Thread(target=asyncio.run, args=(self._show_station(stop_id, cancel_event),))
        thread.start()
        return thread, cancel_event

    async def _show_station(self, stop_id: str, cancel_event: threading.Event):
        stop_name = self.stop_name(stop_id)
        display = Display(stop_name)
        urls = [
            'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs',
            'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace',
            'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm',
            'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-g',
            'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-jz',
            'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-l',
            'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw',
            # Staten Island Railroad:
            # 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-si'
        ]

        while not cancel_event.is_set():
            logging.info(f'[{stop_name}] Fetching data...')
            async with aiohttp.ClientSession() as session:
                feeds = await asyncio.gather(*(_fetch_feed(url, session) for url in urls))

            arrivals = [
                Arrival(stop, route=self._routes_by_id[entity.trip_update.trip.route_id])
                for feed in feeds
                for entity in feed.entity
                for stop in entity.trip_update.stop_time_update
                if stop.arrival.time
            ]
            logging.info(f'[{stop_name}] Updating image')
            if cancel_event.is_set(): break
            display.refresh(a for a in arrivals if a.stop_id == stop_id)
            logging.info(f'[{stop_name}] Finished updating image')
            cancel_event.wait(timeout=self._refresh_rate)

        logging.info(f'[{stop_name}] Cancelled')


'''
Example stop IDs:
    86th/Broadway: 121
    96th/Broadway: 120
    86th/Central Park West: A20
    Columbus Circle: A24
    Pelham Parkway: 504
    E 180th St: 213
'''

if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--stop_ids', required=True, nargs='+', help='The stop IDs to display (from stops.txt)')
    parser.add_argument('-r', '--refresh_rate', type=int, default=30, help='The refresh rate in seconds')
    args = parser.parse_args()
    Controller(args.stop_ids, args.refresh_rate).run()
