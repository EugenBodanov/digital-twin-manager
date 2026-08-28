import globals


def lambda_function_arn(function_name):
  region = globals.aws_lambda_client.meta.region_name
  account_id = globals.aws_sts_client.get_caller_identity()["Account"]
  return f"arn:aws:lambda:{region}:{account_id}:function:{function_name}"


def iot_rule_arn(rule_name):
  region = globals.aws_iot_client.meta.region_name
  account_id = globals.aws_sts_client.get_caller_identity()["Account"]
  return f"arn:aws:iot:{region}:{account_id}:rule/{rule_name}"
