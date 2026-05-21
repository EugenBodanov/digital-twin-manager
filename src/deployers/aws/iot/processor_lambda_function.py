import deployment_state
from deployers.aws.apply_actions import ACTION_DESTROY, ACTION_DEPLOY
from deployers.aws.core.plan_actions import plan_action
from deployers.base import Deployer
import json
import globals
import os
from botocore.exceptions import ClientError
import util

class ProcessorLambdaFunctionDeployer(Deployer):
  def log(self, message):
    print(f"IoT: {message}")

  def plan(self, previous_iot_device, desired_iot_device):

    previous_function_name = (
      deployment_state.last_applied_processor_lambda_function_name(previous_iot_device)
      if previous_iot_device else None
    )
    desired_function_name = (
      globals.processor_lambda_function_name(desired_iot_device)
      if desired_iot_device else None
    )

    previous_function_name_local = (
      deployment_state.last_applied_processor_lambda_function_name_local(previous_iot_device)
      if previous_iot_device else None
    )
    desired_function_name_local = (
      globals.processor_lambda_function_name_local(desired_iot_device)
      if desired_iot_device else None
    )

    previous_role_name = (
      deployment_state.last_applied_processor_iam_role_name(previous_iot_device)
      if previous_iot_device else None
    )
    desired_role_name = (
      globals.processor_iam_role_name(desired_iot_device)
      if desired_iot_device else None
    )

    if previous_iot_device is None:
      self.log(f"Processor lambda function {desired_function_name} is new.")
      return [
        plan_action(desired_function_name, "lambda_function", action="DEPLOY"),
      ]

    if desired_iot_device is None:
      self.log(f"Processor lambda function {previous_function_name} was removed from config.")
      return [
        plan_action(previous_function_name, "lambda_function", action="DESTROY"),
      ]

    if (previous_function_name == desired_function_name and
            previous_function_name_local == desired_function_name_local and
            previous_role_name == desired_role_name):
      self.log(f"Processor lambda function {desired_function_name} is up to date.")
      return [
        plan_action(desired_function_name, "lambda_function"),
      ]

    if previous_function_name != desired_function_name:
      self.log(f"Processor lambda function name has changed from {previous_function_name} to {desired_function_name}")

    if previous_function_name_local != desired_function_name_local:
      self.log(f"Processor lambda function local name has changed from {previous_function_name_local} to {desired_function_name_local}")

    if previous_role_name != desired_role_name:
      self.log(f"Processor lambda role name has changed from {previous_role_name} to {desired_role_name}")

    return [
      plan_action(previous_function_name, "lambda_function", action="DESTROY"),
      plan_action(desired_function_name, "lambda_function", action="DEPLOY"),
    ]

  def deploy(self, iot_device, function_name=None, role_name=None):
    function_name = function_name or globals.processor_lambda_function_name(iot_device)
    function_name_local = globals.processor_lambda_function_name_local(iot_device)
    role_name = role_name or globals.processor_iam_role_name(iot_device)

    response = globals.aws_iam_client.get_role(RoleName=role_name)
    role_arn = response["Role"]["Arn"]

    path_to_code_folder = os.path.join(globals.project_path(), globals.processor_lfs_path, function_name_local)

    if not os.path.exists(path_to_code_folder):
      path_to_code_folder = os.path.join(globals.project_path(), globals.core_lfs_path, "default-processor")

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
          "DIGITAL_TWIN_INFO": json.dumps(globals.digital_twin_info()),
          "PERSISTER_LAMBDA_NAME": globals.persister_lambda_function_name()
        }
      }
    )

    self.log(f"Created Lambda function: {function_name}")

  def destroy(self, iot_device, function_name=None):
    function_name = function_name or globals.processor_lambda_function_name(iot_device)

    try:
      globals.aws_lambda_client.delete_function(FunctionName=function_name)
      self.log(f"Deleted Lambda function: {function_name}")
    except ClientError as e:
      if e.response["Error"]["Code"] != "ResourceNotFoundException":
        raise

  def info(self, iot_device):
    function_name = globals.processor_lambda_function_name(iot_device)

    try:
      globals.aws_lambda_client.get_function(FunctionName=function_name)
      self.log(f"✅ Processor {function_name} Lambda Function exists: {util.link_to_lambda_function(function_name)}")
    except ClientError as e:
      if e.response["Error"]["Code"] == "ResourceNotFoundException":
        self.log(f"❌ Processor {function_name} Lambda Function missing: {function_name}")
      else:
        raise

  def apply(self, action, iot_device, resource):
    if action["action"] == ACTION_DESTROY:
      self.destroy(
        iot_device,
        function_name=resource,
      )
    elif action["action"] == ACTION_DEPLOY:
      self.deploy(
        iot_device,
        function_name=resource,
        role_name=globals.processor_iam_role_name(iot_device),
      )
    else:
      raise ValueError(f"Unsupported iot_l2 action: {action['action']}")
