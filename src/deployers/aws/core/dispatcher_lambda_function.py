from deployers.base import Deployer
from deployers.aws.core.plan_actions import plan_action
import json
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
      "Environment": {
        "Variables": {
          "DIGITAL_TWIN_INFO": json.dumps(digital_twin_info),
        }
      }
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

    if actual_env.get("DIGITAL_TWIN_INFO") != expected_env["DIGITAL_TWIN_INFO"]:
      changed_fields.append("Environment.DIGITAL_TWIN_INFO")

    return changed_fields

  def plan(self):
    previous_function_name = deployment_state.last_applied_dispatcher_lambda_function_name()
    desired_function_name = globals.dispatcher_lambda_function_name()

    if previous_function_name == desired_function_name:

      self.log(f"Dispatcher Lambda function {desired_function_name} is up to date.")

      return [
        plan_action(desired_function_name, "lambda_function")
      ]

    self.log(f"Dispatcher Lambda function name changed from {previous_function_name} to {desired_function_name}.")

    return [
      plan_action(previous_function_name, "lambda_function", action="DESTROY"),
      plan_action(desired_function_name, "lambda_function", action="DEPLOY"),
    ]

  def deploy(self):
    function_name = globals.dispatcher_lambda_function_name()
    role_name = globals.dispatcher_iam_role_name()

    response = globals.aws_iam_client.get_role(RoleName=role_name)
    role_arn = response["Role"]["Arn"]

    globals.aws_lambda_client.create_function(
      FunctionName=function_name,
      Runtime="python3.13",
      Role=role_arn,
      Handler="lambda_function.lambda_handler", #  file.function
      Code={"ZipFile": util.compile_lambda_function(os.path.join(globals.core_lfs_path, "dispatcher"))},
      Description="",
      Timeout=3, # seconds
      MemorySize=128, # MB
      Publish=True,
      Environment={
        "Variables": {
          "DIGITAL_TWIN_INFO": json.dumps(globals.digital_twin_info()),
        }
      }
    )

    self.log(f"Created Lambda function: {function_name}")

  def destroy(self):
    function_name = globals.dispatcher_lambda_function_name()

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
