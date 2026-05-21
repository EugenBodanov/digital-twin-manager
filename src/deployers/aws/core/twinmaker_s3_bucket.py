from deployers.base import Deployer
from deployers.aws.apply_actions import ACTION_DESTROY, ACTION_DEPLOY
from deployers.aws.core.plan_actions import plan_action
import deployment_state
import globals
import util
from botocore.exceptions import ClientError

class TwinmakerS3BucketDeployer(Deployer):
  def log(self, message):
    print(f"Core: {message}")

  def plan(self):
    previous_bucket_name = deployment_state.last_applied_twinmaker_s3_bucket_name()
    desired_bucket_name = globals.twinmaker_s3_bucket_name()
    previous_region = deployment_state.last_applied_aws_region()
    desired_region = globals.aws_s3_client.meta.region_name

    if (
      previous_bucket_name == desired_bucket_name
      and previous_region == desired_region
    ):
      self.log(f"TwinMaker S3 Bucket {desired_bucket_name} is up to date in {desired_region}.")
      return [
        plan_action(desired_bucket_name, "s3_bucket", region=desired_region)
      ]

    self.log(
      "TwinMaker S3 Bucket will be redeployed: "
      f"{previous_bucket_name} ({previous_region}) -> "
      f"{desired_bucket_name} ({desired_region})."
    )
    return [
      plan_action(
        previous_bucket_name,
        "s3_bucket",
        action="DESTROY",
        region=previous_region,
      ),
      plan_action(
        desired_bucket_name,
        "s3_bucket",
        action="DEPLOY",
        region=desired_region,
      ),
    ]

  def deploy(self, bucket_name=None):
    bucket_name = bucket_name or globals.twinmaker_s3_bucket_name()

    globals.aws_s3_client.create_bucket(
      Bucket=bucket_name,
      CreateBucketConfiguration={
          "LocationConstraint": globals.aws_s3_client.meta.region_name
      }
    )

    globals.aws_s3_client.put_bucket_cors(
        Bucket=bucket_name,
        CORSConfiguration={
          "CORSRules": [
            {
              "AllowedOrigins": ["*"],
              "AllowedMethods": ["GET","HEAD"],
              "AllowedHeaders": ["*"],
              "ExposeHeaders": ["ETag"]
            }
          ]
        }
    )

    self.log(f"Created S3 Bucket: {bucket_name}")

  def destroy(self, bucket_name=None):
    bucket_name = bucket_name or globals.twinmaker_s3_bucket_name()

    if util.destroy_s3_bucket(bucket_name):
      self.log(f"Deleted S3 bucket: {bucket_name}")

  def info(self):
    bucket_name = globals.twinmaker_s3_bucket_name()

    try:
      globals.aws_s3_client.head_bucket(Bucket=bucket_name)
      self.log(f"✅ Twinmaker S3 Bucket exists: {util.link_to_s3_bucket(bucket_name)}")
    except ClientError as e:
      if int(e.response["Error"]["Code"]) == 404:
        self.log(f"❌ Twinmaker S3 Bucket missing: {bucket_name}")
      else:
        raise

  def apply(self, action, resource):
    if action["action"] == ACTION_DESTROY:
      self.destroy(resource)
    elif action["action"] == ACTION_DEPLOY:
      self.deploy(resource)
    else:
      raise ValueError(f"Unsupported core_l4 action: {action['action']}")
