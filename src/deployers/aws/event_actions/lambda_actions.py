import hashlib

import deployment_state
from deployers.aws.core.json_helpers import normalized_json, content_changed
from deployers.aws.core.plan_actions import plan_action
from deployers.base import Deployer
import json
import os
import time
import globals
import util
from botocore.exceptions import ClientError

class LambdaActionsDeployer(Deployer):
  def log(self, message):
    print(f"Event Actions: {message}")


  def _create_iam_role(self, role_name):
    globals.aws_iam_client.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps(
          {
            "Version": "2012-10-17",
            "Statement": [
              {
                "Effect": "Allow",
                "Principal": {
                  "Service": "lambda.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
              }
            ]
          }
        )
    )

    self.log(f"Created IAM role: {role_name}")

    policy_arns = [
      "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
    ]

    for policy_arn in policy_arns:
      globals.aws_iam_client.attach_role_policy(
        RoleName=role_name,
        PolicyArn=policy_arn
      )

      self.log(f"Attached IAM policy ARN: {policy_arn}")

  def _destroy_iam_role(self, role_name):
    try:
      response = globals.aws_iam_client.list_attached_role_policies(RoleName=role_name)
      for policy in response["AttachedPolicies"]:
          globals.aws_iam_client.detach_role_policy(RoleName=role_name, PolicyArn=policy["PolicyArn"])

      response = globals.aws_iam_client.list_role_policies(RoleName=role_name)
      for policy_name in response["PolicyNames"]:
          globals.aws_iam_client.delete_role_policy(RoleName=role_name, PolicyName=policy_name)

      response = globals.aws_iam_client.list_instance_profiles_for_role(RoleName=role_name)
      for profile in response["InstanceProfiles"]:
        globals.aws_iam_client.remove_role_from_instance_profile(
          InstanceProfileName=profile["InstanceProfileName"],
          RoleName=role_name
        )

      globals.aws_iam_client.delete_role(RoleName=role_name)
      self.log(f"Deleted IAM role: {role_name}")
    except ClientError as e:
      if e.response["Error"]["Code"] != "NoSuchEntity":
        raise

  def _info_iam_role(self, role_name):
    try:
      globals.aws_iam_client.get_role(RoleName=role_name)
      self.log(f"✅ IAM Role exists: {role_name} {util.link_to_iam_role(role_name)}")
    except ClientError as e:
      if e.response["Error"]["Code"] == "NoSuchEntity":
        self.log(f"❌ IAM Role missing: {role_name}")
      else:
        raise


  def _create_lambda_function(self, function_name, path_to_code_folder=None, local_function_name=None):
    role_name = function_name

    response = globals.aws_iam_client.get_role(RoleName=role_name)
    role_arn = response["Role"]["Arn"]

    if path_to_code_folder == None:
      path_to_code_folder = os.path.join(globals.event_action_lfs_path, local_function_name)

    globals.aws_lambda_client.create_function(
      FunctionName=function_name,
      Runtime="python3.13",
      Role=role_arn,
      Handler="lambda_function.lambda_handler", #  file.function
      Code={"ZipFile": util.compile_lambda_function(path_to_code_folder)},
      Description="",
      Timeout=3, # seconds
      MemorySize=128, # MB
      Publish=True,
      Environment={
        "Variables": {
          "DIGITAL_TWIN_INFO": json.dumps(globals.digital_twin_info())
        }
      }
    )

    self.log(f"Created Lambda function: {function_name}")

  def _destroy_lambda_function(self, function_name):
    try:
      globals.aws_lambda_client.delete_function(FunctionName=function_name)
      self.log(f"Deleted Lambda function: {function_name}")
    except ClientError as e:
      if e.response["Error"]["Code"] != "ResourceNotFoundException":
        raise

  def _info_lambda_function(self, function_name):
    try:
      globals.aws_lambda_client.get_function(FunctionName=function_name)
      self.log(f"✅ Lambda Function exists: {function_name} {util.link_to_lambda_function(function_name)}")
    except ClientError as e:
      if e.response["Error"]["Code"] == "ResourceNotFoundException":
        self.log(f"❌ Lambda Function missing: {function_name}")
      else:
        raise

  def _root_event_id(self, event: dict) -> str:
    payload = json.dumps(
      event,
      sort_keys=True,
      separators=(",", ":"),
    )

    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]

    action = event.get("action", {})
    action_type = action.get("type", "unknown")
    function_name = action.get("functionName", "unknown")

    return f"{action_type}:{function_name}:{digest}"

  def _root_events_by_id(self, actions: list[dict]) -> dict[str, dict]:
    events_by_id = {}

    for event in actions:
        event_id = self._root_event_id(event)

        if event_id in events_by_id:
            raise ValueError(f"Duplicate root event action id: {event_id}")

        events_by_id[event_id] = event

    return events_by_id

  def _ordered_root_ids(self, previous_actions_by_id: dict[str, dict], desired_actions_by_id: dict[str, dict]):

    root_ids = []

    for action_id, action in previous_actions_by_id.items():
      root_ids.append(action_id)

    for action_id, action in desired_actions_by_id.items():
      if action_id not in root_ids:
        root_ids.append(action_id)

    return root_ids

  def plan(self):
    previous_actions = deployment_state.last_applied_config_events
    desired_actions = globals.config_events

    previous_actions_by_id = self._root_events_by_id(previous_actions)
    desired_actions_by_id = self._root_events_by_id(desired_actions)

    actions = []

    for action_id in self._ordered_root_ids(previous_actions_by_id, desired_actions_by_id):
      previous_action = previous_actions_by_id.get(action_id)
      desired_action = desired_actions_by_id.get(action_id)

      if previous_action is None:
        self.log(f"Event Action {action_id} is new.")
        actions.append(plan_action(action_id, "event_action", action="DEPLOY"))
        continue

      if desired_action is None:
        self.log(f"Event Action {action_id} was removed from config.")
        actions.append(plan_action(action_id, "event_action", action="DESTROY"))
        continue

      if not content_changed(previous_action, desired_action):
        self.log(f"Event Action {action_id} is up to date.")
        actions.append(plan_action(action_id, "event_action"))
        continue

      self.log(f"Event Action {action_id} has changed.")
      actions.extend([
        plan_action(action_id, "event_action", action="DESTROY"),
        plan_action(action_id, "event_action", action="DEPLOY"),
      ])

    return actions


  def deploy(self):
    for event in globals.config_events:
      a = event["action"]
      event_action_iam_role_name = globals.event_action_iam_role_name(a)
      event_action_lambda_function_name = globals.event_action_lambda_function_name(a)
      event_action_local_function_name = a["functionName"]

      if a["type"] == "lambda" and not a.get("external"):
        self._create_iam_role(event_action_iam_role_name)

        self.log(f"Waiting for propagation...")
        time.sleep(20)

        self._create_lambda_function(event_action_lambda_function_name, a.get("pathToCode"), event_action_local_function_name)

  def destroy(self):
    for event in globals.config_events:
      a = event["action"]
      event_action_iam_role_name = globals.event_action_iam_role_name(a)
      event_action_lambda_function_name = globals.event_action_lambda_function_name(a)

      if a["type"] == "lambda" and not a.get("external"):
        self._destroy_lambda_function(event_action_lambda_function_name)
        self._destroy_iam_role(event_action_iam_role_name)

  def info(self):
    for event in globals.config_events:
      a = event["action"]
      event_action_iam_role_name = globals.event_action_iam_role_name(a)
      event_action_lambda_function_name = globals.event_action_lambda_function_name(a)

      if a["type"] == "lambda" and not a.get("external"):
        self._info_iam_role(event_action_iam_role_name)
        self._info_lambda_function(event_action_lambda_function_name)
