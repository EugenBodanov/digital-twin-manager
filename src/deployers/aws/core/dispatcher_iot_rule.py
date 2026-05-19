from deployers.base import Deployer
from deployers.aws.core.aws_arns import iot_rule_arn, lambda_function_arn
from deployers.aws.core.lambda_permission import LambdaPermissionPlanner
from deployers.aws.core.plan_actions import plan_action
import globals
import redeployment_state
import util
from botocore.exceptions import ClientError

class DispatcherIotRuleDeployer(Deployer):
  LAMBDA_PERMISSION_STATEMENT_ID = "iot-invoke"

  def log(self, message):
    print(f"Core: {message}")

  def _topic_rule(self, rule_name):
    try:
      response = globals.aws_iot_client.get_topic_rule(ruleName=rule_name)
      return response["rule"]
    except ClientError as e:
      if e.response["Error"]["Code"] in ["ResourceNotFoundException", "UnauthorizedException"]:
        return None
      raise

  def _actions(self, function_name):
    return [
      {
        "lambda": {
          "functionArn": lambda_function_arn(function_name)
        }
      }
    ]

  def _drifted_fields(self, topic_rule, expected_topic, expected_function_name):
    expected_sql = f"SELECT * FROM '{expected_topic}'"
    expected_actions = self._actions(expected_function_name)
    drifted_fields = []

    if topic_rule.get("sql") != expected_sql:
      drifted_fields.append("sql")

    if topic_rule.get("ruleDisabled") is not False:
      drifted_fields.append("ruleDisabled")

    if topic_rule.get("actions", []) != expected_actions:
      drifted_fields.append("actions")

    return drifted_fields

  def _lambda_permission_plan(
    self,
    previous_rule_name,
    desired_rule_name,
    previous_function_name,
    desired_function_name
  ):
    previous_source_arn = None
    if previous_rule_name:
      previous_source_arn = iot_rule_arn(previous_rule_name)

    return LambdaPermissionPlanner(
      resource="dispatcher_iot_rule_lambda_permission",
      parent_resource="dispatcher_iot_rule",
      label="Dispatcher IoT Rule Lambda permission",
      statement_id=self.LAMBDA_PERMISSION_STATEMENT_ID,
      principal_service="iot.amazonaws.com",
      action="lambda:InvokeFunction",
      log=self.log
    ).plan(
      previous_function_name,
      desired_function_name,
      previous_source_arn,
      iot_rule_arn(desired_rule_name)
    )

  def plan(self):
    previous_rule_name = redeployment_state.last_applied_dispatcher_iot_rule_name()
    desired_rule_name = globals.dispatcher_iot_rule_name()
    previous_topic = redeployment_state.last_applied_dispatcher_iot_rule_topic()
    desired_topic = globals.dispatcher_iot_rule_topic()
    previous_function_name = redeployment_state.last_applied_dispatcher_lambda_function_name()
    desired_function_name = globals.dispatcher_lambda_function_name()
    desired_dt_name = globals.config["digital_twin_name"]

    actions = plan_action(
      "dispatcher_iot_rule",
      "iot_rule",
      previous_rule_name=previous_rule_name,
      desired_rule_name=desired_rule_name,
      previous_topic=previous_topic,
      desired_topic=desired_topic,
      previous_function_name=previous_function_name,
      desired_function_name=desired_function_name,
      child_changes=[],
    )

    permission_action = self._lambda_permission_plan(
      previous_rule_name,
      desired_rule_name,
      previous_function_name,
      desired_function_name
    )
    actions["child_changes"].append(permission_action)

    if permission_action["blocked"]:
      actions["blocked"] = True
      actions["blockers"].extend(permission_action["blockers"])

    if not previous_rule_name:
      if self._topic_rule(desired_rule_name) is not None:
        self.log(
          "STATE_SYNC_REQUIRED Desired Dispatcher IoT Rule already exists: "
          f"{desired_rule_name}"
        )

        actions.update({
          "action": "CREATE",
          "blocked": True,
          "state_sync_required": True,
        })
        actions["blockers"].append(
          f"Desired IoT rule already exists: {desired_rule_name}"
        )
        return actions

      self.log(f"CREATE Dispatcher IoT Rule: {desired_rule_name}")

      actions.update({
        "action": "CREATE",
      })
      return actions

    previous_rule = self._topic_rule(previous_rule_name)
    drift_fields = []

    if previous_rule is None:
      drift_fields.append("missing")
    else:
      drift_fields = self._drifted_fields(
        previous_rule,
        previous_topic,
        previous_function_name
      )

    if drift_fields:
      if drift_fields == ["missing"]:
        if previous_rule_name != desired_rule_name:
          previous_dt_name = redeployment_state.last_applied_digital_twin_name()

          self.log(
            "CREATE Dispatcher IoT Rule recovery: "
            f"{previous_rule_name} -> {desired_rule_name} "
            f"(digital_twin_name changed: {previous_dt_name} -> {desired_dt_name}); "
            "requires allow_recovery"
          )
        else:
          self.log(
            "CREATE Dispatcher IoT Rule recovery: "
            f"{previous_rule_name}; requires allow_recovery"
          )

        actions.update({
          "action": "CREATE",
          "required_flags": ["allow_recovery"],
          "drift_fields": drift_fields,
        })

        if (
          previous_rule_name != desired_rule_name
          and self._topic_rule(desired_rule_name) is not None
        ):
          self.log(
            "STATE_SYNC_REQUIRED Desired Dispatcher IoT Rule already exists: "
            f"{desired_rule_name}"
          )

          actions["blocked"] = True
          actions["blockers"].append(
            f"Desired IoT rule already exists: {desired_rule_name}"
          )
          actions["state_sync_required"] = True

        return actions

      self.log(
        "DRIFT_UNKNOWN Dispatcher IoT Rule differs from state: "
        f"{previous_rule_name}; fields={drift_fields}; no safe update reference"
      )
      actions.update({
        "action": "DRIFT_UNKNOWN",
        "blocked": True,
        "drift_fields": drift_fields,
      })
      actions["blockers"].append("Actual IoT rule differs from last-applied state")
      return actions

    if previous_rule_name != desired_rule_name:
      previous_dt_name = redeployment_state.last_applied_digital_twin_name()

      self.log(
        "REPLACE_REQUIRED Dispatcher IoT Rule: "
        f"{previous_rule_name} -> {desired_rule_name} "
        f"(digital_twin_name changed: {previous_dt_name} -> {desired_dt_name})"
      )
      self.log(f"UPDATE Dispatcher IoT Rule topic: {previous_topic} -> {desired_topic}")

      actions.update({
        "action": "REPLACE_REQUIRED",
        "required_flags": ["allow_replacement"],
      })

      if self._topic_rule(desired_rule_name) is not None:
        self.log(
          "STATE_SYNC_REQUIRED Desired Dispatcher IoT Rule already exists: "
          f"{desired_rule_name}"
        )

        actions["blocked"] = True
        actions["blockers"].append(
          f"Desired IoT rule already exists: {desired_rule_name}"
        )
        actions["state_sync_required"] = True

      return actions

    changed_fields = self._drifted_fields(
      previous_rule,
      desired_topic,
      desired_function_name
    )

    if changed_fields:
      self.log(
        "UPDATE Dispatcher IoT Rule: "
        f"{desired_rule_name}; fields={changed_fields}"
      )
      actions.update({
        "action": "UPDATE",
        "changed_fields": changed_fields,
      })
      return actions

    self.log(f"NO_CHANGE Dispatcher IoT Rule: {desired_rule_name}")
    return actions

  def deploy(self):
    rule_name = globals.dispatcher_iot_rule_name()
    topic = globals.dispatcher_iot_rule_topic()
    sql = f"SELECT * FROM '{topic}'"

    function_name = globals.dispatcher_lambda_function_name()

    globals.aws_iot_client.create_topic_rule(
      ruleName=rule_name,
      topicRulePayload={
        "sql": sql,
        "description": "",
        "actions": self._actions(function_name),
        "ruleDisabled": False
      }
    )

    self.log(f"Created IoT rule: {rule_name}")

    globals.aws_lambda_client.add_permission(
      FunctionName=function_name,
      StatementId=self.LAMBDA_PERMISSION_STATEMENT_ID,
      Action="lambda:InvokeFunction",
      Principal="iot.amazonaws.com",
      SourceArn=iot_rule_arn(rule_name)
    )

    self.log(f"Added permission to Lambda function so the rule can invoke the function.")

  def destroy(self):
    function_name = globals.dispatcher_lambda_function_name()
    rule_name = globals.dispatcher_iot_rule_name()

    try:
      globals.aws_lambda_client.remove_permission(
          FunctionName=function_name,
          StatementId=self.LAMBDA_PERMISSION_STATEMENT_ID
      )
      self.log(f"Removed permission from Lambda function: {rule_name}, {function_name}")
    except globals.aws_lambda_client.exceptions.ResourceNotFoundException:
      pass

    if util.iot_rule_exists(rule_name):
      try:
        globals.aws_iot_client.delete_topic_rule(ruleName=rule_name)
        self.log(f"Deleted IoT Rule: {rule_name}")
      except globals.aws_iot_client.exceptions.ResourceNotFoundException:
        pass

  def info(self):
    rule_name = globals.dispatcher_iot_rule_name()

    try:
      globals.aws_iot_client.get_topic_rule(ruleName=rule_name)
      self.log(f"✅ Dispatcher Iot Rule exists: {util.link_to_iot_rule(rule_name)}")
    except ClientError as e:
      if e.response["Error"]["Code"] == "UnauthorizedException":
        self.log(f"❌ Dispatcher IoT Rule missing: {rule_name}")
      else:
        raise
