<?php
try {
    if (isset($_GET['wms_app_token']) && isset($_GET['wms_hostname']) && isset($_GET['time_table_id'])) {
        $wms_app_token = $_GET['wms_app_token'];
        $wms_hostname = $_GET['wms_hostname'];
        $time_table_id = $_GET['time_table_id'];

        $output = shell_exec("/var/www/timetable_status/main.py " . $time_table_id . " " . $wms_hostname . " " . $wms_app_token . " 2>&1");
        echo trim($output);
    } else {
        echo("timetable_status: Invalid parameters");
    }
} catch (Exception $e) {
    echo("timetable_status: Exception");
}
?>
