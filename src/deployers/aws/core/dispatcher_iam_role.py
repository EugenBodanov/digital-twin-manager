from deployers.base import Deployer
from deployers.aws.core.json_helpers import normalized_json
from deployers.aws.core.plan_actions import plan_action
import json
import time
import globals
import redeployment_state
import util
from botocore.exceptions import ClientError

class DispatcherIamRoleDeployer(Deployer):
  def log(self, message):
    print(f"Core: {message}")

  def _role(self, role_name):
    try:
      response = globals.aws_iam_client.get_role(RoleName=role_name)
      return response["Role"]
    except ClientError as e:
      if e.response["Error"]["Code"] == "NoSuchEntity":
        return None
      raise

  def _role_exists(self, role_name):
    return self._role(role_name) is not None

  def _role_policy_document(self):
    return {
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

  def _policy_arns(self):
    return {
      "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
      "arn:aws:iam::aws:policy/service-role/AWSLambdaRole",
    }

  def _attached_policy_arns(self, role_name):
    response = globals.aws_iam_client.list_attached_role_policies(RoleName=role_name)
    return {
      policy["PolicyArn"]
      for policy in response["AttachedPolicies"]
    }

  def _drift_fields(self, role_name):
    role = self._role(role_name)

    if role is None:
      return ["missing"]

    drift_fields = []
    actual_assume_role_policy = role["AssumeRolePolicyDocument"]
    expected_assume_role_policy = self._role_policy_document()

    if (
      normalized_json(actual_assume_role_policy)
      != normalized_json(expected_assume_role_policy)
    ):
      drift_fields.append("AssumeRolePolicyDocument")

    if self._attached_policy_arns(role_name) != self._policy_arns():
      drift_fields.append("AttachedPolicies")

    return drift_fields

  def plan(self):

    previous_role_name = redeployment_state.last_applied_dispatcher_iam_role_name()
    desired_role_name = globals.dispatcher_iam_role_name()
    desired_dt_name = globals.config["digital_twin_name"]

    actions = plan_action(
      "dispatcher_iam_role",
      "iam_role",
      previous_role_name=previous_role_name,
      desired_role_name=desired_role_name,
    )

    if not previous_role_name:
      if self._role_exists(desired_role_name):
        self.log(
          "STATE_SYNC_REQUIRED Desired Dispatcher IAM Role already exists: "
          f"{desired_role_name}; delete it if unmanaged"
        )

        actions.update({
          "action": "CREATE",
          "blocked": True,
          "blockers": [
            f"Desired IAM role already exists: {desired_role_name}"
          ],
          "state_sync_required": True,
        })
        return actions

      self.log(f"CREATE Dispatcher IAM Role: {desired_role_name}")

      actions.update({
        "action": "CREATE",
      })
      return actions

    drift_fields = self._drift_fields(previous_role_name)

    if drift_fields:
      if drift_fields == ["missing"]:
        if previous_role_name != desired_role_name:
          previous_dt_name = redeployment_state.last_applied_digital_twin_name()

          self.log(
            "CREATE Dispatcher IAM Role recovery: "
            f"{previous_role_name} -> {desired_role_name} "
            f"(digital_twin_name changed: {previous_dt_name} -> {desired_dt_name}); "
            "requires allow_recovery"
          )
        else:
          self.log(
            "CREATE Dispatcher IAM Role recovery: "
            f"{previous_role_name}; requires allow_recovery"
          )

        actions.update({
          "action": "CREATE",
          "required_flags": ["allow_recovery"],
          "drift_fields": drift_fields,
        })

        if (
          previous_role_name != desired_role_name
          and self._role_exists(desired_role_name)
        ):
          self.log(
            "STATE_SYNC_REQUIRED Desired Dispatcher IAM Role already exists: "
            f"{desired_role_name}; delete it if unmanaged"
          )

          actions["blocked"] = True
          actions["blockers"].append(
            f"Desired IAM role already exists: {desired_role_name}"
          )
          actions["state_sync_required"] = True

        return actions

      self.log(
        "DRIFT_UNKNOWN Dispatcher IAM Role differs from state: "
        f"{previous_role_name}; fields={drift_fields}; no safe update reference"
      )
      actions.update({
        "action": "DRIFT_UNKNOWN",
        "blocked": True,
        "drift_fields": drift_fields,
        "blockers": ["Actual IAM role differs from last-applied state"],
      })
      return actions

    # IAM role names are immutable.
    if previous_role_name != desired_role_name:
      previous_dt_name = redeployment_state.last_applied_digital_twin_name()

      self.log(
        "REPLACE_REQUIRED Dispatcher IAM Role: "
        f"{previous_role_name} -> {desired_role_name} "
        f"(digital_twin_name changed: {previous_dt_name} -> {desired_dt_name})"
      )

      actions.update({
        "action": "REPLACE_REQUIRED",
        "required_flags": ["allow_replacement"],
      })


      # Replacement cannot create the desired role if that role already exists
      if self._role_exists(desired_role_name):
        self.log(
          "STATE_SYNC_REQUIRED Desired Dispatcher IAM Role already exists: "
          f"{desired_role_name}; delete it if unmanaged"
        )

        actions["blocked"] = True
        actions["blockers"].append(
          f"Desired IAM role already exists: {desired_role_name}"
        )
        actions["state_sync_required"] = True


      return actions

    self.log(f"NO_CHANGE Dispatcher IAM Role: {desired_role_name}")

    return actions


  def deploy(self):
    role_name = globals.dispatcher_iam_role_name()

    globals.aws_iam_client.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps(
          self._role_policy_document()
        )
    )

    self.log(f"Created IAM role: {role_name}")

    for policy_arn in self._policy_arns():
      globals.aws_iam_client.attach_role_policy(
        RoleName=role_name,
        PolicyArn=policy_arn
      )

      self.log(f"Attached IAM policy ARN: {policy_arn}")

    self.log(f"Waiting for propagation...")

    time.sleep(20)

  def destroy(self):
    role_name = globals.dispatcher_iam_role_name()

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

  def info(self):
    role_name = globals.dispatcher_iam_role_name()

    try:
      globals.aws_iam_client.get_role(RoleName=role_name)
      self.log(f"✅ Dispatcher IAM Role exists: {util.link_to_iam_role(role_name)}")
    except ClientError as e:
      if e.response["Error"]["Code"] == "NoSuchEntity":
        self.log(f"❌ Dispatcher IAM Role missing: {role_name}")
      else:
        raise
