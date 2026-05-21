from deployers.base import Deployer
from deployers.aws.apply_actions import ACTION_DESTROY, ACTION_DEPLOY
from deployers.aws.core.plan_actions import plan_action
import json
import os
import globals
import deployment_state
import util
from botocore.exceptions import ClientError


class EventRegistryRegisterLambdaFunctionDeployer(Deployer):
    def log(self, message):
        print(f"Core: {message}")

    def plan(self):
        previous_function_name = deployment_state.last_applied_event_registry_register_lambda_function_name()
        desired_function_name = globals.event_registry_register_lambda_function_name()
        previous_role_name = deployment_state.last_applied_event_registry_register_iam_role_name()
        desired_role_name = globals.event_registry_register_iam_role_name()

        if (
            previous_function_name == desired_function_name
            and previous_role_name == desired_role_name
        ):
            self.log(f"Event-Registry-Register Lambda function {desired_function_name} is up to date.")
            return [
                plan_action(desired_function_name, "lambda_function")
            ]

        if previous_function_name != desired_function_name:
            self.log(f"Event-Registry-Register Lambda function name changed from {previous_function_name} to {desired_function_name}.")
        if previous_role_name != desired_role_name:
            self.log(f"Event-Registry-Register IAM role name changed from {previous_role_name} to {desired_role_name}.")

        return [
            plan_action(previous_function_name, "lambda_function", action="DESTROY"),
            plan_action(desired_function_name, "lambda_function", action="DEPLOY"),
        ]

    def deploy(self, function_name=None, role_name=None):
        function_name = function_name or globals.event_registry_register_lambda_function_name()
        role_name = role_name or globals.event_registry_register_iam_role_name()
        ssm_prefix = globals.ssm_registry_prefix()

        role_arn = globals.aws_iam_client.get_role(RoleName=role_name)["Role"]["Arn"]

        response = globals.aws_lambda_client.create_function(
            FunctionName=function_name,
            Runtime="python3.13",
            Role=role_arn,
            Handler="lambda_function.lambda_handler",
            Code={"ZipFile": util.compile_lambda_function(
                os.path.join(globals.core_lfs_path, "event-registry-register")
            )},
            Description="FunctionRegistry: register/deregister custom event target addresses via SSM",
            Timeout=10,
            MemorySize=128,
            Publish=True,
            Environment={"Variables": {"SSM_REGISTRY_PREFIX": ssm_prefix}}
        )

        self.log(f"Created Lambda function: {function_name}")
        url_response = globals.aws_lambda_client.create_function_url_config(
            FunctionName=function_name,
            AuthType="NONE"
        )

        globals.aws_lambda_client.add_permission(
            FunctionName=function_name,
            StatementId="AllowPublicFunctionUrl",
            Action="lambda:InvokeFunctionUrl",
            Principal="*",
            FunctionUrlAuthType="NONE"
        )

        function_url = url_response["FunctionUrl"]
        self.log(f"Created Function URL (Telefonbuch): {function_url}")

        print(f"\n{'='*60}")
        print(f"  Function URL: {function_url}")
        print(f"")
        print(f"  POST {function_url}")
        print(f'    {{"action":"register","eventName":"my-event","address":"<lambda-name|arn|https-url>","addressType":"lambda"}}')
        print(f"")
        print(f"  POST {function_url}")
        print(f'    {{"action":"deregister","eventName":"my-event"}}')
        print(f"")
        print(f"  GET  {function_url}")
        print(f"")
        print(f"  SSM Pfad: {ssm_prefix}/{{eventName}}")
        print(f"{'='*60}\n")

    def destroy(self, function_name=None):
        function_name = function_name or globals.event_registry_register_lambda_function_name()
        for fn in [
            lambda: globals.aws_lambda_client.delete_function_url_config(FunctionName=function_name),
            lambda: globals.aws_lambda_client.delete_function(FunctionName=function_name),
        ]:
            try:
                fn()
            except ClientError as e:
                if e.response["Error"]["Code"] != "ResourceNotFoundException":
                    raise
        self.log(f"Deleted Lambda function: {function_name}")

    def info(self):
        function_name = globals.event_registry_register_lambda_function_name()
        try:
            globals.aws_lambda_client.get_function(FunctionName=function_name)
            try:
                url = globals.aws_lambda_client.get_function_url_config(FunctionName=function_name)["FunctionUrl"]
                self.log(f"✅ Event-Registry-Register Lambda exists: {util.link_to_lambda_function(function_name)}")
                self.log(f"   FunctionRegistry URL: {url}")
            except ClientError:
                self.log(f"✅ Event-Registry-Register Lambda exists (no URL): {util.link_to_lambda_function(function_name)}")
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                self.log(f"❌ Event-Registry-Register Lambda missing: {function_name}")
            else:
                raise

    def apply(self, action, resource):
        if action["action"] == ACTION_DESTROY:
            self.destroy(resource)
        elif action["action"] == ACTION_DEPLOY:
            self.deploy(resource)
        else:
            raise ValueError(f"Unsupported core_l2 action: {action['action']}")
