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

    def check_timetable_status(self, time_table_id: str) -> int:
        """
        Returns 1 if the timetable is active, 0 otherwise.

        State logic:
          - STATE_FORCE_ACTIVE (2)   → always 1
          - STATE_FORCE_INACTIVE (0) → always 0
          - STATE_CHECK_TIME (1)     → check items

        Item types:
          - dayOfWeek == 0 → calendar range (specific dates, same month/year)
          - dayOfWeek != 0 → weekly recurring (ISO weekday: 1=Mon, 7=Sun)
        """
        timetable = self.get_timetable(time_table_id)
        state = timetable.get('state')

        if state == self.STATE_FORCE_ACTIVE:
            return 1
        if state == self.STATE_FORCE_INACTIVE:
            return 0

        # STATE_CHECK_TIME: evaluate each item
        now = datetime.datetime.now()
        current_date = now.date()
        current_time = now.time()
        current_weekday = now.isoweekday()  # 1=Mon, 7=Sun

        for item in timetable.get('items', []):
            from_dow = item['from'].get('dayOfWeek', 0)
            to_dow = item['to'].get('dayOfWeek', 0)

            # Parse time range (format: HH:MM:SS)
            time_from = datetime.time.fromisoformat(item['time']['from'])
            time_to = datetime.time.fromisoformat(item['time']['to'])

            if not (time_from <= current_time <= time_to):
                continue

            if from_dow == 0:
                # Calendar-based range (specific dates within same month/year)
                year = item['year']
                month = item['month']
                start_date = datetime.date(year, month, item['from']['day'])

                # If end day < start day, the range wraps into the next month
                end_day = item['to']['day']
                if end_day < item['from']['day']:
                    end_date = (
                        datetime.date(year, month, 1)
                        + datetime.timedelta(days=32)
                    ).replace(day=end_day)
                else:
                    end_date = datetime.date(year, month, end_day)

                if start_date <= current_date <= end_date:
                    return 1

            else:
                # Weekly recurring range (ISO weekday: 1=Mon, 7=Sun)
                if from_dow <= to_dow:
                    in_range = from_dow <= current_weekday <= to_dow
                else:
                    # Wrap-around (e.g., Fri=5 to Mon=1)
                    in_range = current_weekday >= from_dow or current_weekday <= to_dow

                if in_range:
                    return 1

        return 0
