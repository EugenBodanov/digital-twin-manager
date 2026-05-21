from deployers.base import Deployer
from deployers.aws.apply_actions import ACTION_DESTROY, ACTION_DEPLOY
from deployers.aws.core.plan_actions import plan_action
import json
import os
import globals
import deployment_state
import util
from botocore.exceptions import ClientError

class EventFeedbackLambdaFunctionDeployer(Deployer):
  def log(self, message):
    print(f"Core: {message}")

  def plan(self):
    previous_function_name = deployment_state.last_applied_event_feedback_lambda_function_name()
    desired_function_name = globals.event_feedback_lambda_function_name()
    previous_role_name = deployment_state.last_applied_event_feedback_iam_role_name()
    desired_role_name = globals.event_feedback_iam_role_name()

    if (
      previous_function_name == desired_function_name
      and previous_role_name == desired_role_name
    ):
      self.log(f"Event-Feedback Lambda function {desired_function_name} is up to date.")
      return [
        plan_action(desired_function_name, "lambda_function")
      ]

    if previous_function_name != desired_function_name:
      self.log(f"Event-Feedback Lambda function name changed from {previous_function_name} to {desired_function_name}.")
    if previous_role_name != desired_role_name:
      self.log(f"Event-Feedback IAM role name changed from {previous_role_name} to {desired_role_name}.")

    return [
      plan_action(previous_function_name, "lambda_function", action="DESTROY"),
      plan_action(desired_function_name, "lambda_function", action="DEPLOY"),
    ]
  
  def deploy(self, function_name=None, role_name=None):
    function_name = function_name or globals.event_feedback_lambda_function_name()
    role_name = role_name or globals.event_feedback_iam_role_name()

    response = globals.aws_iam_client.get_role(RoleName=role_name)
    role_arn = response["Role"]["Arn"]

    globals.aws_lambda_client.create_function(
      FunctionName=function_name,
      Runtime="python3.13",
      Role=role_arn,
      Handler="lambda_function.lambda_handler", #  file.function
      Code={"ZipFile": util.compile_lambda_function(os.path.join(globals.core_lfs_path, "event-feedback"))},
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

  def destroy(self, function_name=None):
    function_name = function_name or globals.event_feedback_lambda_function_name()

    try:
      globals.aws_lambda_client.delete_function(FunctionName=function_name)
      self.log(f"Deleted Lambda function: {function_name}")
    except ClientError as e:
      if e.response["Error"]["Code"] != "ResourceNotFoundException":
        raise

  def info(self):
    function_name = globals.event_feedback_lambda_function_name()

    try:
      globals.aws_lambda_client.get_function(FunctionName=function_name)
      self.log(f"✅ Event-Feedback Lambda Function exists: {util.link_to_lambda_function(function_name)}")
    except ClientError as e:
      if e.response["Error"]["Code"] == "ResourceNotFoundException":
        self.log(f"❌ Event-Feedback Lambda Function missing: {function_name}")
      else:
        raise

  def apply(self, action, resource):
    if action["action"] == ACTION_DESTROY:
      self.destroy(resource)
    elif action["action"] == ACTION_DEPLOY:
      self.deploy(resource)
    else:
      raise ValueError(f"Unsupported core_l2 action: {action['action']}")
