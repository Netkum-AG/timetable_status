#!/usr/bin/env python3
import sys

from wms_interface import WildixInterface

if __name__ == '__main__':

    if len(sys.argv[1:]) < 3:
        print(f'timetable_status param error {sys.argv[1:]}')
    else:
        time_table_id, wms_hostname, wms_app_token = sys.argv[1:4]

        interface = WildixInterface(
            wms_hostname=wms_hostname,
            wms_app_token=wms_app_token
        )

        if not interface.check_login():
            print('WMS login error')
        else:
            print(interface.check_timetable_status(time_table_id))
