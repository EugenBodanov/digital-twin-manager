import deployment_state
from deployers.aws.apply_actions import ACTION_DESTROY, ACTION_DEPLOY
from deployers.aws.core.plan_actions import plan_action
from deployers.base import Deployer
from dependency_graph import plan_graph_ids
import os
import globals
import util
from botocore.exceptions import ClientError

class ColdArchiveMoverLambdaFunctionDeployer(Deployer):
  def log(self, message):
    print(f"Core: {message}")

  def plan(self):
    previous_function_name = deployment_state.last_applied_cold_archive_mover_lambda_function_name()
    desired_function_name = globals.cold_archive_mover_lambda_function_name()
    previous_role_name = deployment_state.last_applied_cold_archive_mover_iam_role_name()
    desired_role_name = globals.cold_archive_mover_iam_role_name()

    if previous_function_name == desired_function_name and previous_role_name == desired_role_name:
      self.log(f"Cold to Archive Mover Lambda Function {desired_function_name} is up to date.")
      return [
        plan_action(
          desired_function_name,
          "lambda_function",
          graph_id=plan_graph_ids.COLD_ARCHIVE_MOVER_LAMBDA,
        )
      ]

    if previous_function_name != desired_function_name:
      self.log(f"Cold to Archive Mover Lambda Function name changed from {previous_function_name} to {desired_function_name}.")
    if previous_role_name != desired_role_name:
      self.log(f"Cold to Archive Mover IAM role name changed from {previous_role_name} to {desired_role_name}.")

    return [
      plan_action(
        previous_function_name,
        "lambda_function",
        action="DESTROY",
        graph_id=plan_graph_ids.COLD_ARCHIVE_MOVER_LAMBDA,
      ),
      plan_action(
        desired_function_name,
        "lambda_function",
        action="DEPLOY",
        graph_id=plan_graph_ids.COLD_ARCHIVE_MOVER_LAMBDA,
      ),
    ]

  def deploy(self, function_name=None, role_name=None):
    function_name = function_name or globals.cold_archive_mover_lambda_function_name()
    role_name = role_name or globals.cold_archive_mover_iam_role_name()

    response = globals.aws_iam_client.get_role(RoleName=role_name)
    role_arn = response["Role"]["Arn"]

    globals.aws_lambda_client.create_function(
      FunctionName=function_name,
      Runtime="python3.13",
      Role=role_arn,
      Handler="lambda_function.lambda_handler", #  file.function
      Code={"ZipFile": util.compile_lambda_function(os.path.join(globals.core_lfs_path, "cold-to-archive-mover"))},
      Description="",
      Timeout=3, # seconds
      MemorySize=128, # MB
      Publish=True,
      Environment=util.lambda_environment({
        "COLD_STORAGE_SIZE_IN_DAYS": str(globals.config["cold_storage_size_in_days"]),
        "SOURCE_S3_BUCKET_NAME": globals.cold_s3_bucket_name(),
        "TARGET_S3_BUCKET_NAME": globals.archive_s3_bucket_name()
      })
    )

    self.log(f"Created Lambda function: {function_name}")

  def destroy(self, function_name=None):
    function_name = function_name or globals.cold_archive_mover_lambda_function_name()

    try:
      globals.aws_lambda_client.delete_function(FunctionName=function_name)
      self.log(f"Deleted Lambda function: {function_name}")
    except ClientError as e:
      if e.response["Error"]["Code"] != "ResourceNotFoundException":
        raise

  def info(self):
    function_name = globals.cold_archive_mover_lambda_function_name()

    try:
      globals.aws_lambda_client.get_function(FunctionName=function_name)
      self.log(f"✅ Cold to Archive Mover Lambda Function exists: {util.link_to_lambda_function(function_name)}")
    except ClientError as e:
      if e.response["Error"]["Code"] == "ResourceNotFoundException":
        self.log(f"❌ Cold to Archive Mover Lambda Function missing: {function_name}")
      else:
        raise

  def apply(self, action, resource):
    if action["action"] == ACTION_DESTROY:
      self.destroy(resource)
    elif action["action"] == ACTION_DEPLOY:
      self.deploy(resource)
    else:
      raise ValueError(f"Unsupported core_l3_cold action: {action['action']}")
