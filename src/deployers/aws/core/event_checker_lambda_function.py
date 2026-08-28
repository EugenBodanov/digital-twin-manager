from deployers.base import Deployer
from deployers.aws.apply_actions import ACTION_DESTROY, ACTION_DEPLOY
from deployers.aws.core.plan_actions import plan_action
from dependency_graph import plan_graph_ids
import json
import os
import globals
import deployment_state
import util
from botocore.exceptions import ClientError

class EventCheckerLambdaFunctionDeployer(Deployer):
  def log(self, message):
    print(f"Core: {message}")

  def plan(self):
    previous_function_name = deployment_state.last_applied_event_checker_lambda_function_name()
    desired_function_name = globals.event_checker_lambda_function_name()
    previous_role_name = deployment_state.last_applied_event_checker_iam_role_name()
    desired_role_name = globals.event_checker_iam_role_name()
    previous_lambda_chain_name = deployment_state.last_applied_lambda_chain_step_function_name()
    desired_lambda_chain_name = globals.lambda_chain_step_function_name()
    previous_event_feedback_function_name = deployment_state.last_applied_event_feedback_lambda_function_name()
    desired_event_feedback_function_name = globals.event_feedback_lambda_function_name()
    previous_config_events = deployment_state.last_applied_config_events
    desired_config_events = globals.config_events

    if (
      previous_function_name == desired_function_name
      and previous_role_name == desired_role_name
      and previous_lambda_chain_name == desired_lambda_chain_name
      and previous_event_feedback_function_name == desired_event_feedback_function_name
      and previous_config_events == desired_config_events
    ):
      self.log(f"Event-Checker Lambda function {desired_function_name} is up to date.")
      return [
        plan_action(
          desired_function_name,
          "lambda_function",
          graph_id=plan_graph_ids.EVENT_CHECKER_LAMBDA,
        )
      ]

    if previous_function_name != desired_function_name:
      self.log(f"Event-Checker Lambda function name changed from {previous_function_name} to {desired_function_name}.")
    if previous_role_name != desired_role_name:
      self.log(f"Event-Checker IAM role name changed from {previous_role_name} to {desired_role_name}.")
    if previous_lambda_chain_name != desired_lambda_chain_name:
      self.log(f"Lambda Chain Step Function name changed from {previous_lambda_chain_name} to {desired_lambda_chain_name}.")
    if previous_event_feedback_function_name != desired_event_feedback_function_name:
      self.log(f"Event-Feedback Lambda function name changed from {previous_event_feedback_function_name} to {desired_event_feedback_function_name}.")
    if previous_config_events != desired_config_events:
      self.log("Event-Checker Lambda function config_events have changed.")

    return [
      plan_action(
        previous_function_name,
        "lambda_function",
        action="DESTROY",
        graph_id=plan_graph_ids.EVENT_CHECKER_LAMBDA,
      ),
      plan_action(
        desired_function_name,
        "lambda_function",
        action="DEPLOY",
        graph_id=plan_graph_ids.EVENT_CHECKER_LAMBDA,
      ),
    ]

  def deploy(self, function_name=None, role_name=None):
    function_name = function_name or globals.event_checker_lambda_function_name()
    role_name = role_name or globals.event_checker_iam_role_name()

    response = globals.aws_iam_client.get_role(RoleName=role_name)
    role_arn = response["Role"]["Arn"]

    region = globals.aws_lambda_client.meta.region_name
    account_id = globals.aws_sts_client.get_caller_identity()['Account']
    lambda_chain_name = globals.lambda_chain_step_function_name()
    lambda_chain_arn = f"arn:aws:states:{region}:{account_id}:stateMachine:{lambda_chain_name}"

    event_feedback_lambda_function = globals.event_feedback_lambda_function_name()
    response = globals.aws_lambda_client.get_function(FunctionName=event_feedback_lambda_function)
    event_feedback_lambda_function_arn = response["Configuration"]["FunctionArn"]

    globals.aws_lambda_client.create_function(
      FunctionName=function_name,
      Runtime="python3.13",
      Role=role_arn,
      Handler="lambda_function.lambda_handler", #  file.function
      Code={
        "ZipFile": util.compile_lambda_function(
          os.path.join(globals.core_lfs_path, "event-checker"),
          extra_files={
            "config_events.json": json.dumps(
              globals.config_events,
              ensure_ascii=False,
              separators=(",", ":"),
            )
          },
        )
      },
      Description="",
      Timeout=900, # seconds
      MemorySize=128, # MB
      Publish=True,
      Environment=util.lambda_environment({
        "DIGITAL_TWIN_NAME": globals.config["digital_twin_name"],
        "TWINMAKER_WORKSPACE_NAME": globals.twinmaker_workspace_name(),
        "LAMBDA_CHAIN_STEP_FUNCTION_ARN": lambda_chain_arn,
        "EVENT_FEEDBACK_LAMBDA_FUNCTION_ARN": event_feedback_lambda_function_arn,
        "SSM_REGISTRY_PREFIX": globals.ssm_registry_prefix()
      })
    )

    self.log(f"Created Lambda function: {function_name}")

  def destroy(self, function_name=None):
    function_name = function_name or globals.event_checker_lambda_function_name()

    try:
      globals.aws_lambda_client.delete_function(FunctionName=function_name)
      self.log(f"Deleted Lambda function: {function_name}")
    except ClientError as e:
      if e.response["Error"]["Code"] != "ResourceNotFoundException":
        raise

  def info(self):
    function_name = globals.event_checker_lambda_function_name()

    try:
      globals.aws_lambda_client.get_function(FunctionName=function_name)
      self.log(f"✅ Event-Checker Lambda Function exists: {util.link_to_lambda_function(function_name)}")
    except ClientError as e:
      if e.response["Error"]["Code"] == "ResourceNotFoundException":
        self.log(f"❌ Event-Checker Lambda Function missing: {function_name}")
      else:
        raise

  def apply(self, action, resource):
    if action["action"] == ACTION_DESTROY:
      self.destroy(resource)
    elif action["action"] == ACTION_DEPLOY:
      self.deploy(resource)
    else:
      raise ValueError(f"Unsupported core_l2 action: {action['action']}")
