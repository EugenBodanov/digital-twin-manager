# TwinMaker Hierarchy Deployer

The TwinMaker hierarchy deployer is a separate deployment phase that creates the AWS IoT TwinMaker entity tree and attaches components to entities. It is implemented in `src/deployers/aws/hierarchy/twinmaker_hierarchy.py`.

This deployer is not part of Core L1-L5 and is not part of IoT L1/L2/L4. It runs after Core and IoT infrastructure have been created.

## Deployment Position

The `deploy` command runs the hierarchy phase in this order:

1. Core deployers create shared resources, including the TwinMaker workspace in Core L4.
2. IoT deployers create per-device resources, including TwinMaker Component Types in IoT L4.
3. The hierarchy deployer creates Entities and attaches Components from `config_hierarchy.json`.
4. Event action deployers and init values run afterward.

The `destroy` command runs the hierarchy phase in the reverse flow, after event actions and before IoT resources are removed.

## Input Configuration

The hierarchy deployer reads `config_hierarchy.json`.

- Entries with `"type": "entity"` become TwinMaker Entities.
- Entries with `"type": "component"` become Components attached to the current parent Entity.
- Nested entity entries create parent-child relationships in TwinMaker.
- Component entries reference Component Types that must already exist.

## Entity Creation

For each entity entry, the deployer calls TwinMaker `create_entity` with:

- `workspaceId`: the TwinMaker workspace name from `digital_twin_name`.
- `entityId`: the configured `id`.
- `entityName`: the configured `name`, or the `id` if `name` is missing.
- `parentEntityId`: set only when the entity is nested under another entity.

Child entities are deployed recursively.

## Component Attachment

For each component entry, the deployer attaches the component to its parent entity using TwinMaker `update_entity` with `componentUpdates`.

The Component Type is resolved in one of two ways:

- If the component entry defines `componentTypeId`, that value is used directly.
- Otherwise, the deployer derives the Component Type ID as `<digitalTwinName>-<iotDeviceId>`.

Because of this dependency, every derived `iotDeviceId` must match a device in `config_iot_devices.json` so that IoT L4 can create the corresponding Component Type first.

## What This Deployer Does Not Create

The hierarchy deployer does not create:

- TwinMaker workspaces, S3 buckets, or IAM roles. These belong to Core L4.
- TwinMaker Component Types. These belong to IoT L4.
- TwinMaker Scenes.
- DynamoDB or S3 telemetry storage.
- Event action Lambdas or runtime event rules.

## Destroy Behavior

During `destroy`, the deployer deletes the configured root entities from `config_hierarchy.json` with recursive deletion enabled. This removes child entities and attached components inside the TwinMaker workspace.

It does not delete Component Types or the TwinMaker workspace itself. Those are removed later by the IoT and Core destroy phases.

## Info Behavior

During `info`, the deployer verifies:

- Expected Entities exist.
- Nested Entities have the expected parent.
- Expected Components are attached to their parent Entity.
- Attached Components use the expected Component Type ID.
