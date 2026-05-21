import deployment_state
from deployers.aws.core.json_helpers import content_changed
from deployers.aws.core.plan_actions import plan_action
from deployers.base import Deployer
import time
import globals
import util
from botocore.exceptions import ClientError

class TwinmakerHierarchyDeployer(Deployer):
  def log(self, message):
    print(f"Hierarchy: {message}")

  def _root_entities_by_id(self, hierarchy):
    return {entity["id"]: entity for entity in hierarchy}

  def _ordered_root_ids(self, previous_hierarchy, desired_hierarchy):
    previous_entities = self._root_entities_by_id(previous_hierarchy)
    root_ids = []

    for entity in previous_hierarchy:
      root_ids.append(entity["id"])

    for entity in desired_hierarchy:
      if entity["id"] not in previous_entities:
        root_ids.append(entity["id"])

    return root_ids


  def _deploy_twinmaker_entity(self, entity_info, parent_info=None):
    create_entity_params = {
      "workspaceId": globals.twinmaker_workspace_name(),
      "entityName": entity_info.get("name") or entity_info["id"],
      "entityId": entity_info["id"],
    }

    if parent_info is not None:
      create_entity_params["parentEntityId"] = parent_info["id"]

    response = globals.aws_twinmaker_client.create_entity(**create_entity_params)

    self.log(f"Created IoT TwinMaker Entity: {response["entityId"]}")

    for child in entity_info["children"]:
      if child["type"] == "entity":
        self._deploy_twinmaker_entity(child, entity_info)
      elif child["type"] == "component":
        self._deploy_twinmaker_component(child, entity_info)

  def _deploy_twinmaker_component(self, component_info, parent_info):
    if "componentTypeId" in component_info:
      component_type_id = component_info["componentTypeId"]
    else:
      component_type_id = f"{globals.config["digital_twin_name"]}-{component_info["iotDeviceId"]}"

    globals.aws_twinmaker_client.update_entity(
      workspaceId=globals.twinmaker_workspace_name(),
      entityId=parent_info["id"],
      componentUpdates={
          component_info["name"]: {
              "updateType": "CREATE",
              "componentTypeId": component_type_id
          }
      }
    )

    self.log(f"Created IoT TwinMaker Component: {component_info["name"]}")

  def plan(self):
    previous_hierarchy = deployment_state.last_applied_config_hierarchy
    desired_hierarchy = globals.config_hierarchy

    previous_workspace_name = deployment_state.last_applied_twinmaker_workspace_name()
    desired_workspace_name = globals.twinmaker_workspace_name()

    previous_entities = self._root_entities_by_id(previous_hierarchy)
    desired_entities = self._root_entities_by_id(desired_hierarchy)
    actions = []

    for entity_id in self._ordered_root_ids(previous_hierarchy, desired_hierarchy):
      previous_entity = previous_entities.get(entity_id)
      desired_entity = desired_entities.get(entity_id)

      if previous_entity is None:
        self.log(f"TwinMaker Hierarchy root entity {entity_id} is new.")
        actions.append(
          plan_action(entity_id, "twinmaker_hierarchy", action="DEPLOY")
        )
        continue

      if desired_entity is None:
        self.log(f"TwinMaker Hierarchy root entity {entity_id} was removed from config.")
        actions.append(
          plan_action(entity_id, "twinmaker_hierarchy", action="DESTROY")
        )
        continue

      if (
        previous_workspace_name == desired_workspace_name
        and not content_changed(previous_entity, desired_entity)
      ):
        self.log(f"TwinMaker Hierarchy root entity {entity_id} is up to date.")
        actions.append(
          plan_action(entity_id, "twinmaker_hierarchy")
        )
        continue

      if previous_workspace_name != desired_workspace_name:
        self.log(
          "TwinMaker Hierarchy workspace has changed from "
          f"{previous_workspace_name} to {desired_workspace_name}."
        )

      if content_changed(previous_entity, desired_entity):
        self.log(f"TwinMaker Hierarchy root entity {entity_id} has changed.")

      actions.extend([
        plan_action(entity_id, "twinmaker_hierarchy", action="DESTROY"),
        plan_action(entity_id, "twinmaker_hierarchy", action="DEPLOY"),
      ])

    return actions


  def deploy(self):
    for entity in globals.config_hierarchy:
      self._deploy_twinmaker_entity(entity)

  def destroy(self):
    workspace_name = globals.twinmaker_workspace_name()
    deleting_entities = []

    for entity in globals.config_hierarchy:
      try:
        globals.aws_twinmaker_client.delete_entity(workspaceId=workspace_name, entityId=entity["id"], isRecursive=True)
        deleting_entities.append(entity)
      except ClientError as e:
        if e.response["Error"]["Code"] != "ResourceNotFoundException":
          raise

    for entity in deleting_entities:
      while True:
        try:
          globals.aws_twinmaker_client.get_entity(workspaceId=workspace_name, entityId=entity["id"])
          time.sleep(2)
        except ClientError as e:
          if e.response["Error"]["Code"] == "ResourceNotFoundException":
            break
          else:
            raise

      self.log(f"Deleted IoT TwinMaker Entity: {entity["id"]}")

  def info(self, hierarchy=None, parent=None):
    workspace_name = globals.twinmaker_workspace_name()

    if hierarchy is None:
      hierarchy = globals.config_hierarchy

    for entry in hierarchy:
      if entry["type"] == "entity":
        try:
          response = globals.aws_twinmaker_client.get_entity(workspaceId=workspace_name, entityId=entry["id"])
          self.log(f"✅ IoT TwinMaker Entity exists: {util.link_to_twinmaker_entity(workspace_name, entry["id"])}")

          if parent is not None and parent["entityId"] != response.get("parentEntityId"):
            self.log(f"❌ IoT TwinMaker Entity {entry["id"]} is missing parent: {parent["entityId"]}")

          if "children" in entry:
            self.info(entry["children"], response)
        except ClientError as e:
          if e.response["Error"]["Code"] == "ResourceNotFoundException":
            self.log(f"❌ IoT TwinMaker Entity missing: {entry["id"]}")
          else:
            raise

      elif entry["type"] == "component":
        if parent is None:
          continue

        if entry["name"] not in parent.get("components", {}):
          self.log(f"❌ IoT TwinMaker Entity {parent["entityId"]} is missing component: {entry["name"]}")
          continue

        self.log(f"✅ IoT TwinMaker Component exists: {util.link_to_twinmaker_component(workspace_name, parent["entityId"], entry["name"])}")

        component_info = parent["components"][entry["name"]]

        if "componentTypeId" in entry:
          entry_component_type_id = entry["componentTypeId"]
        else:
          entry_component_type_id = f"{globals.config["digital_twin_name"]}-{entry["iotDeviceId"]}"

        if component_info["componentTypeId"] != entry_component_type_id:
          self.log(f"❌ IoT TwinMaker Component {entry["name"]} has the wrong component type: {component_info["componentTypeId"]}")
