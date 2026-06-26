import datetime
import requests


class WildixInterface:

    # Timetable states
    STATE_FORCE_INACTIVE = 0
    STATE_CHECK_TIME = 1
    STATE_FORCE_ACTIVE = 2

    def __init__(self, wms_hostname: str, wms_app_token: str):
        self.wms_hostname = wms_hostname.rstrip('/')
        self.wms_app_token = wms_app_token
        self._headers = {'Authorization': f'Bearer {wms_app_token}'}

    def check_login(self) -> bool:
        resp = requests.get(
            url=f'{self.wms_hostname}/api/v1/PBX/version/',
            headers=self._headers
        )
        return resp.status_code == 200

    def get_timetable(self, time_table_id: str) -> dict:
        resp = requests.get(
            url=f'{self.wms_hostname}/api/v1/Dialplan/timeTables/',
            params={'responseType': 'json'},
            headers=self._headers
        )
        resp.raise_for_status()
        records = resp.json()['result']['records']
        for record in records:
            if str(record['id']) == str(time_table_id):
                return record
        raise ValueError(f'Timetable ID {time_table_id} not found')

    @staticmethod
    def _in_time_range(time_from: datetime.time, time_to: datetime.time, current: datetime.time) -> bool:
        """
        time.to = "00:00:00" means end of day (midnight of next day).
        Any time >= time_from matches in that case.
        """
        if time_to == datetime.time(0, 0, 0):
            return current >= time_from
        return time_from <= current <= time_to

    def check_timetable_status(self, time_table_id: str, now: datetime.datetime = None) -> int:
        """
        Returns 1 if the timetable is active, 0 otherwise.

        State logic:
          - STATE_FORCE_ACTIVE (2)   → always 1
          - STATE_FORCE_INACTIVE (0) → always 0
          - STATE_CHECK_TIME (1)     → check items

        Item types:
          - dayOfWeek == 0 → calendar range (specific dates)
          - dayOfWeek != 0 → weekly recurring (ISO weekday: 1=Mon, 7=Sun)

        Special cases:
          - time.to == "00:00:00" means end of day (midnight of next day)
          - Calendar items with year == 0 are placeholder/empty items, skipped
          - Calendar ranges where to.day < from.day wrap into the next month
        """
        timetable = self.get_timetable(time_table_id)
        state = timetable.get('state')

        if state == self.STATE_FORCE_ACTIVE:
            return 1
        if state == self.STATE_FORCE_INACTIVE:
            return 0

        if now is None:
            now = datetime.datetime.now()

        current_date = now.date()
        current_time = now.time()
        current_weekday = now.isoweekday()  # 1=Mon, 7=Sun

        for item in timetable.get('items', []):
            from_dow = item['from'].get('dayOfWeek', 0)
            to_dow = item['to'].get('dayOfWeek', 0)

            time_from = datetime.time.fromisoformat(item['time']['from'])
            time_to = datetime.time.fromisoformat(item['time']['to'])

            if not self._in_time_range(time_from, time_to, current_time):
                continue

            if from_dow == 0:
                # Each field: 0 = wildcard (any)
                year = item['year']
                month = item['month']
                from_day = item['from']['day']
                to_day = item['to']['day']

                if from_day != 0 and to_day < from_day:
                    # Cross-month range: build actual dates and check directly
                    ref_year = year if year != 0 else current_date.year
                    ref_month = month if month != 0 else current_date.month
                    start_date = datetime.date(ref_year, ref_month, from_day)
                    end_date = (
                        datetime.date(ref_year, ref_month, 1)
                        + datetime.timedelta(days=32)
                    ).replace(day=to_day)
                    if not (start_date <= current_date <= end_date):
                        continue
                else:
                    # Normal range: check each field independently (0 = wildcard)
                    if year != 0 and current_date.year != year:
                        continue
                    if month != 0 and current_date.month != month:
                        continue
                    if from_day != 0 and not (from_day <= current_date.day <= to_day):
                        continue

                return 1

            else:
                # Weekly recurring (ISO weekday: 1=Mon, 7=Sun)
                if from_dow <= to_dow:
                    in_range = from_dow <= current_weekday <= to_dow
                else:
                    # Wrap-around (e.g., Fri=5 to Mon=1)
                    in_range = current_weekday >= from_dow or current_weekday <= to_dow

                if in_range:
                    return 1

        return 0
