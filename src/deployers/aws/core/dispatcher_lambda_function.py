from deployers.aws.apply_actions import ACTION_DESTROY, ACTION_DEPLOY
from deployers.base import Deployer
from deployers.aws.core.plan_actions import plan_action
from dependency_graph import plan_graph_ids
import os
import globals
import deployment_state
import util
from botocore.exceptions import ClientError

class DispatcherLambdaFunctionDeployer(Deployer):
  def log(self, message):
    print(f"Core: {message}")

  def _function_configuration(self, function_name):
    try:
      response = globals.aws_lambda_client.get_function(FunctionName=function_name)
      return response["Configuration"]
    except ClientError as e:
      if e.response["Error"]["Code"] == "ResourceNotFoundException":
        return None
      raise

  def _function_configuration_from_digital_twin_info(self, digital_twin_info):
    return {
      "Runtime": "python3.13",
      "Handler": "lambda_function.lambda_handler",
      "Timeout": 3,
      "MemorySize": 128,
      "Environment": util.lambda_environment({
        "DIGITAL_TWIN_NAME": digital_twin_info["config"]["digital_twin_name"],
      })
    }

  def _previous_function_configuration(self):
    return self._function_configuration_from_digital_twin_info(
      deployment_state.last_applied_digital_twin_info()
    )

  def _desired_function_configuration(self):
    return self._function_configuration_from_digital_twin_info(
      globals.digital_twin_info()
    )

  def _drift_fields(self, actual_configuration, expected_configuration):
    changed_fields = []

    for field in ["Runtime", "Handler", "Timeout", "MemorySize"]:
      if actual_configuration.get(field) != expected_configuration[field]:
        changed_fields.append(field)

    actual_env = actual_configuration.get("Environment", {}).get("Variables", {})
    expected_env = expected_configuration["Environment"]["Variables"]

    for name, expected_value in expected_env.items():
      if actual_env.get(name) != expected_value:
        changed_fields.append(f"Environment.{name}")

    return changed_fields

  def plan(self):
    previous_function_name = deployment_state.last_applied_dispatcher_lambda_function_name()
    desired_function_name = globals.dispatcher_lambda_function_name()

    if previous_function_name == desired_function_name:

      self.log(f"Dispatcher Lambda function {desired_function_name} is up to date.")

      return [
        plan_action(
          desired_function_name,
          "lambda_function",
          graph_id=plan_graph_ids.DISPATCHER_LAMBDA,
        )
      ]

    self.log(f"Dispatcher Lambda function name changed from {previous_function_name} to {desired_function_name}.")

    return [
      plan_action(
        previous_function_name,
        "lambda_function",
        action="DESTROY",
        graph_id=plan_graph_ids.DISPATCHER_LAMBDA,
      ),
      plan_action(
        desired_function_name,
        "lambda_function",
        action="DEPLOY",
        graph_id=plan_graph_ids.DISPATCHER_LAMBDA,
      ),
    ]

  def deploy(self, function_name=None, role_name=None):
    function_name = function_name or globals.dispatcher_lambda_function_name()
    role_name = role_name or globals.dispatcher_iam_role_name()

    response = globals.aws_iam_client.get_role(RoleName=role_name)
    role_arn = response["Role"]["Arn"]
    function_configuration = self._desired_function_configuration()

    globals.aws_lambda_client.create_function(
      FunctionName=function_name,
      Role=role_arn,
      Code={"ZipFile": util.compile_lambda_function(os.path.join(globals.core_lfs_path, "dispatcher"))},
      Description="",
      Publish=True,
      **function_configuration,
    )

    self.log(f"Created Lambda function: {function_name}")

  def destroy(self, function_name=None):
    function_name = function_name or globals.dispatcher_lambda_function_name()

    try:
      globals.aws_lambda_client.delete_function(FunctionName=function_name)
      self.log(f"Deleted Lambda function: {function_name}")
    except ClientError as e:
      if e.response["Error"]["Code"] != "ResourceNotFoundException":
        raise

  def info(self):
    function_name = globals.dispatcher_lambda_function_name()

    try:
      globals.aws_lambda_client.get_function(FunctionName=function_name)
      self.log(f"✅ Dispatcher Lambda Function exists: {util.link_to_lambda_function(function_name)}")
    except ClientError as e:
      if e.response["Error"]["Code"] == "ResourceNotFoundException":
        self.log(f"❌ Dispatcher Lambda Function missing: {function_name}")
      else:
        raise

  def apply(self, action, resource):
    if action["action"] == ACTION_DESTROY:
      self.destroy(resource)
    elif action["action"] == ACTION_DEPLOY:
      self.deploy(resource)
    else:
      raise ValueError(f"Unsupported core_l1 action: {action['action']}")
