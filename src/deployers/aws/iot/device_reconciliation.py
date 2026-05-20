import deployment_state
import globals


def _devices_by_id(iot_devices):
  return {iot_device["id"]: iot_device for iot_device in iot_devices}


def reconciled_iot_devices():
  previous_devices = _devices_by_id(deployment_state.last_applied_config_iot_devices)
  desired_devices = _devices_by_id(globals.config_iot_devices)

  device_ids = []
  for iot_device in deployment_state.last_applied_config_iot_devices:
    device_ids.append(iot_device["id"])

  for iot_device in globals.config_iot_devices:
    if iot_device["id"] not in previous_devices:
      device_ids.append(iot_device["id"])

  return [
    (previous_devices.get(iot_device_id), desired_devices.get(iot_device_id))
    for iot_device_id in device_ids
  ]
