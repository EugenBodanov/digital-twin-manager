# Operational Runbook

The `digital-twin-manager` is an interactive deployment tool. It uses local configuration files to provision AWS resources via Boto3, and all runtime operations are handled natively by AWS services. Because the tool **does not use a state file** (like Terraform), AWS itself is the source of truth, and resource names are the primary tracking mechanism.

## Core CLI Commands

- **`deploy`:** Provisions all infrastructure in a strict dependency order (Core → IoT → Hierarchy → Events → Init Values).
- **`destroy`:** Tears down the infrastructure in reverse order.
- **`info`:** Scans AWS to verify which expected resources currently exist.

## Pre-Deployment Checklist

Before running `deploy`, ensure these files are correctly configured:

1.  **`config.json`:** Verify `digital_twin_name` follows strict regex rules (`[A-Za-z0-9_-]+`, max 10 chars).
2.  **`config_iot_devices.json`:** Define devices, properties, and optional `initValue` fields.
3.  **`config_hierarchy.json`:** Map the devices to TwinMaker Entities and Components.
4.  **`config_events.json`:** Define event rules and actions (ensuring spaces around operators like `<` or `>`).
5.  **`config_credentials.json`:** Ensure valid AWS keys and region are set (**NEVER commit this file**).

## Event Registry / FunctionRegistry Operations

During Core L2 deployment, the manager creates an Event Registry Register Lambda and prints its Function URL. The endpoint stores custom event target addresses in SSM Parameter Store under `/<digitalTwinName>/event-registry/{eventName}`.

The Function URL is deployed without authentication (`AuthType="NONE"`), so treat it as a public endpoint:

- Do not publish the URL in shared logs, tickets, or documentation.
- Add authentication or network controls before production use.
- Delete or disable the Function URL if the registry is not required.
- Use `info` to confirm the Function URL exists, and check the SSM path directly to verify registry entries.

## Recommended Workflow

Because the tool currently creates not updates, the safest workflow for configuration changes is:

1.  Run `info` to check current state.
2.  Run `destroy` to clear old infrastructure.
3.  Update JSON configs.
4.  Run `deploy` to provision the new setup.
5.  Run a **Runtime Smoke Test** by publishing an MQTT message to `<digitalTwinName>/iot-data` and verifying the data appears in the DynamoDB hot table.

## Key Troubleshooting & Limitations

- **Resource Already Exists:** Since there is no update engine, if a deploy fails halfway or a resource name collides, you must run `destroy` or manually delete the conflicting AWS resource before redeploying.
- **Renaming Dangers:** Never change `digital_twin_name` or `iotDeviceId` between deployments without destroying first, otherwise, the tool will lose track of the old resources.
- **S3 Deletion:** During manual cleanup, remember that S3 buckets must be emptied before they can be deleted.
- **Public Registry Endpoint:** If the Event Registry Register Function URL was created during deploy, confirm whether it should remain enabled. It is unauthenticated by default.
