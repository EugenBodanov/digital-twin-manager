import deployment_state
from deployers.aws.core.plan_actions import plan_action
from deployers.base import Deployer
import globals
import util
from botocore.exceptions import ClientError

class ArchiveS3BucketDeployer(Deployer):
  def log(self, message):
    print(f"Core: {message}")

  def plan(self):
    previous_bucket_name = deployment_state.last_applied_archive_s3_bucket_name()
    desired_bucket_name = globals.archive_s3_bucket_name()

    previous_region = deployment_state.last_applied_aws_region()
    desired_region = globals.aws_s3_client.meta.region_name

    if previous_bucket_name == desired_bucket_name and previous_region == desired_region:
      self.log(f"Archive S3 Bucket {desired_bucket_name} is up to date in {desired_region}.")
      return [
        plan_action(
          desired_bucket_name,
          "s3_bucket",
        )
      ]

    self.log(
      "Archive S3 Bucket will be redeployed: "
      f"{previous_bucket_name} ({previous_region}) -> "
      f"{desired_bucket_name} ({desired_region})."
    )
    return [
      plan_action(previous_bucket_name, "s3_bucket", action="DESTROY"),
      plan_action(desired_bucket_name, "s3_bucket", action="DEPLOY")
    ]

  def deploy(self):
    bucket_name = globals.archive_s3_bucket_name()

    globals.aws_s3_client.create_bucket(
      Bucket=bucket_name,
      CreateBucketConfiguration={
          "LocationConstraint": globals.aws_s3_client.meta.region_name
      }
    )

    self.log(f"Created S3 Bucket: {bucket_name}")

  def destroy(self):
    bucket_name = globals.archive_s3_bucket_name()

    if util.destroy_s3_bucket(bucket_name):
      self.log(f"Deleted S3 bucket: {bucket_name}")

  def info(self):
    bucket_name = globals.archive_s3_bucket_name()

    try:
      globals.aws_s3_client.head_bucket(Bucket=bucket_name)
      self.log(f"✅ Archive S3 Bucket exists: {util.link_to_s3_bucket(bucket_name)}")
    except ClientError as e:
      if int(e.response["Error"]["Code"]) == 404:
        self.log(f"❌ Archive S3 Bucket missing: {bucket_name}")
      else:
        raise
