# IoT Device Infrastructure

Unlike the Core infrastructure, which creates shared resources for the entire digital twin, the IoT infrastructure creates specific AWS resources for every individual device defined in `config_iot_devices.json`.

The deployment is organized into three specific layers, executed in the order of **L1 → L2 → L4** (and destroyed in the strict reverse order of **L4 → L2 → L1**). Notably, there is no IoT L3 layer because storage is handled by the shared Core L3 infrastructure.

---

## Deployment Layers Breakdown

### IoT L1: Device Identity and Connectivity

- Creates the AWS IoT Thing, which represents the device in AWS IoT Core.
- Generates a certificate, public key, and private key to allow the device to authenticate and publish MQTT messages.
- Stores authentication files locally in an `iot_devices_auth/` directory.
- Creates and attaches an IoT policy to enable device connectivity.

### IoT L2: Device-Specific Processing

- Creates a unique Processor Lambda and IAM Role for each configured device.
- Unlike the shared Dispatcher Lambda (which only routes messages), the Processor Lambda handles device-specific tasks like normalizing payloads, converting units, and validating values.
- The deployer uses custom code for the processor if it exists, or automatically falls back to a default generic processor.
- After processing, this Lambda passes the data to the shared Persister Lambda.

### IoT L4: TwinMaker Component Types

- Creates an AWS IoT TwinMaker Component Type for each device.
- Defines the data structure, including property names, data types, flags indicating whether the data is time-series and stored externally.
- Sets up data reader functions that point to the shared hot-reader Lambda. Since TwinMaker stores only the digital twin model and not the actual telemetry data, these functions act as a bridge, allowing TwinMaker to dynamically fetch external property values from DynamoDB whenever a user or dashboard requests them.
- This layer only creates the Component Type (the template); attaching these components to the actual digital twin Entities is handled separately by the hierarchy deployer based on `config_hierarchy.json`.
