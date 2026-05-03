# AWS Permissions

This document describes the IAM permissions required by `digital-twin-manager` when it runs against AWS using the credentials from `config_credentials.json`.

The permission set is derived from:

- Direct Boto3 calls in `src/`.
- The command flow in `src/main.py` for `deploy`, `info`, and `destroy`.
- AWS dependent permissions required by services such as Lambda, Step Functions, AWS IoT TwinMaker, and Amazon Managed Grafana.

The policy examples use `Resource: "*"` because the application creates resources with names derived from `digital_twin_name`, IoT device IDs, event action configuration, and generated AWS resource ARNs. A production policy should narrow resources where possible.

## Application-Managed Permissions

These permissions are required for resources that the application currently creates, checks, or destroys as part of its normal command flow.

### STS

Used to resolve the AWS account ID while building ARNs for Lambda permissions, Step Functions, and TwinMaker.

```text
sts:GetCallerIdentity
```

### IAM

Used to create and remove runtime IAM roles for Lambda, Step Functions, TwinMaker, and Grafana. The application also attaches AWS managed policies and writes inline policies to those roles.

```text
iam:CreateRole
iam:GetRole
iam:UpdateAssumeRolePolicy
iam:PutRolePolicy
iam:DeleteRolePolicy
iam:AttachRolePolicy
iam:DetachRolePolicy
iam:ListAttachedRolePolicies
iam:ListRolePolicies
iam:ListInstanceProfilesForRole
iam:RemoveRoleFromInstanceProfile
iam:DeleteRole
iam:PassRole
```

`iam:PassRole` is not called as a Boto3 IAM operation, but it is required when the application passes role ARNs to Lambda, Step Functions, TwinMaker, and Grafana create operations.

### Lambda

Used for core Lambdas, per-device processor Lambdas, optional internal event action Lambdas, Lambda invoke permissions, and the Event Registry Register Function URL.

```text
lambda:CreateFunction
lambda:GetFunction
lambda:DeleteFunction
lambda:AddPermission
lambda:RemovePermission
lambda:CreateFunctionUrlConfig
lambda:GetFunctionUrlConfig
lambda:DeleteFunctionUrlConfig
```

Internal event action Lambdas are only created when `config_events.json` contains an action with `"external": false`. The current checked-in configuration uses `"external": true`, but the application code supports internal actions.

### AWS IoT

Used for IoT Things, certificates, IoT policies, Thing/principal attachments, IoT rules, and init-value publishing.

```text
iot:CreateThing
iot:DescribeThing
iot:DeleteThing
iot:CreateKeysAndCertificate
iot:UpdateCertificate
iot:DeleteCertificate
iot:CreatePolicy
iot:DeletePolicy
iot:DeletePolicyVersion
iot:ListPolicyVersions
iot:AttachPolicy
iot:DetachPolicy
iot:AttachThingPrincipal
iot:DetachThingPrincipal
iot:ListThingPrincipals
iot:ListAttachedPolicies
iot:CreateTopicRule
iot:GetTopicRule
iot:ListTopicRules
iot:DeleteTopicRule
iot:Publish
```

`iot:Publish` is used by the init-values deployer when any configured IoT property has `initValue`. The current `config_iot_devices.json` contains init values, so this permission is part of the active deployment flow.

### EventBridge

Used for scheduled rules that trigger the hot-to-cold and cold-to-archive mover Lambdas.

```text
events:PutRule
events:DescribeRule
events:DeleteRule
events:PutTargets
events:ListTargetsByRule
events:RemoveTargets
```

### DynamoDB

Used for the hot storage table and for creating a table backup before table deletion.

```text
dynamodb:CreateTable
dynamodb:DescribeTable
dynamodb:DeleteTable
dynamodb:CreateBackup
dynamodb:DescribeBackup
```

### S3

Used for TwinMaker, cold storage, and archive buckets. The destroy flow empties buckets, including versioned objects and delete markers, before deleting the buckets.

```text
s3:CreateBucket
s3:PutBucketCORS
s3:GetBucketLocation
s3:ListBucket
s3:ListBucketVersions
s3:DeleteObject
s3:DeleteObjectVersion
s3:DeleteBucket
```

### AWS IoT TwinMaker

Used for the TwinMaker workspace, component types, entities, and entity component attachments.

```text
iottwinmaker:CreateWorkspace
iottwinmaker:GetWorkspace
iottwinmaker:DeleteWorkspace
iottwinmaker:CreateComponentType
iottwinmaker:GetComponentType
iottwinmaker:DeleteComponentType
iottwinmaker:ListComponentTypes
iottwinmaker:CreateEntity
iottwinmaker:GetEntity
iottwinmaker:UpdateEntity
iottwinmaker:DeleteEntity
iottwinmaker:ListEntities
```

### Amazon Managed Grafana

Used for the Grafana workspace created by Core L5.

```text
grafana:CreateWorkspace
grafana:DescribeWorkspace
grafana:DeleteWorkspace
grafana:ListWorkspaces
grafana:TagResource
```

`grafana:TagResource` is required because the application passes tags during `create_workspace`.

### Step Functions

Used for the Lambda Chain state machine.

```text
states:CreateStateMachine
states:DescribeStateMachine
states:DeleteStateMachine
```

## Cleanup and Scaffold Permissions

These permissions exist because the current destroy logic attempts to clean resources that may exist in the TwinMaker workspace, even though the current deploy flow does not create them.

```text
iottwinmaker:ListScenes
iottwinmaker:DeleteScene
```

The application does not create TwinMaker scenes. During `destroy`, `TwinmakerWorkspaceDeployer` lists and deletes scenes before deleting the workspace. This is defensive cleanup for externally-created or future scene resources.

## AWS-Dependent Permissions

These permissions are not direct Boto3 calls in the application code. They may be required by AWS while fulfilling the application-managed operations above.

### Managed Grafana Dependencies

Amazon Managed Grafana can require service-linked role, AWS IAM Identity Center, AWS Organizations, and EC2 describe permissions while creating or managing a workspace.

```text
iam:CreateServiceLinkedRole
sso:CreateManagedApplicationInstance
sso:DeleteManagedApplicationInstance
sso:DescribeRegisteredRegions
sso:GetSharedSsoConfiguration
organizations:DescribeOrganization
ec2:DescribeSecurityGroups
ec2:DescribeSubnets
ec2:GetManagedPrefixListEntries
```

These permissions are included because the application creates a Grafana workspace with AWS SSO authentication and customer-managed permissions.

## Full Practical Policy

The following policy is intended for the IAM principal whose access keys are stored in `config_credentials.json`.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Identity",
      "Effect": "Allow",
      "Action": ["sts:GetCallerIdentity"],
      "Resource": "*"
    },
    {
      "Sid": "IamManagement",
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole",
        "iam:GetRole",
        "iam:UpdateAssumeRolePolicy",
        "iam:PutRolePolicy",
        "iam:DeleteRolePolicy",
        "iam:AttachRolePolicy",
        "iam:DetachRolePolicy",
        "iam:ListAttachedRolePolicies",
        "iam:ListRolePolicies",
        "iam:ListInstanceProfilesForRole",
        "iam:RemoveRoleFromInstanceProfile",
        "iam:DeleteRole",
        "iam:CreateServiceLinkedRole"
      ],
      "Resource": "*"
    },
    {
      "Sid": "PassRolesToManagedServices",
      "Effect": "Allow",
      "Action": ["iam:PassRole"],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "iam:PassedToService": [
            "lambda.amazonaws.com",
            "states.amazonaws.com",
            "iottwinmaker.amazonaws.com",
            "grafana.amazonaws.com"
          ]
        }
      }
    },
    {
      "Sid": "Lambda",
      "Effect": "Allow",
      "Action": [
        "lambda:CreateFunction",
        "lambda:GetFunction",
        "lambda:DeleteFunction",
        "lambda:AddPermission",
        "lambda:RemovePermission",
        "lambda:CreateFunctionUrlConfig",
        "lambda:GetFunctionUrlConfig",
        "lambda:DeleteFunctionUrlConfig"
      ],
      "Resource": "*"
    },
    {
      "Sid": "IoT",
      "Effect": "Allow",
      "Action": [
        "iot:CreateThing",
        "iot:DescribeThing",
        "iot:DeleteThing",
        "iot:CreateKeysAndCertificate",
        "iot:UpdateCertificate",
        "iot:DeleteCertificate",
        "iot:CreatePolicy",
        "iot:DeletePolicy",
        "iot:DeletePolicyVersion",
        "iot:ListPolicyVersions",
        "iot:AttachPolicy",
        "iot:DetachPolicy",
        "iot:AttachThingPrincipal",
        "iot:DetachThingPrincipal",
        "iot:ListThingPrincipals",
        "iot:ListAttachedPolicies",
        "iot:CreateTopicRule",
        "iot:GetTopicRule",
        "iot:ListTopicRules",
        "iot:DeleteTopicRule",
        "iot:Publish"
      ],
      "Resource": "*"
    },
    {
      "Sid": "EventBridge",
      "Effect": "Allow",
      "Action": [
        "events:PutRule",
        "events:DescribeRule",
        "events:DeleteRule",
        "events:PutTargets",
        "events:ListTargetsByRule",
        "events:RemoveTargets"
      ],
      "Resource": "*"
    },
    {
      "Sid": "DynamoDB",
      "Effect": "Allow",
      "Action": [
        "dynamodb:CreateTable",
        "dynamodb:DescribeTable",
        "dynamodb:DeleteTable",
        "dynamodb:CreateBackup",
        "dynamodb:DescribeBackup"
      ],
      "Resource": "*"
    },
    {
      "Sid": "S3",
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:PutBucketCORS",
        "s3:GetBucketLocation",
        "s3:ListBucket",
        "s3:ListBucketVersions",
        "s3:DeleteObject",
        "s3:DeleteObjectVersion",
        "s3:DeleteBucket"
      ],
      "Resource": "*"
    },
    {
      "Sid": "IoTTwinMaker",
      "Effect": "Allow",
      "Action": [
        "iottwinmaker:CreateWorkspace",
        "iottwinmaker:GetWorkspace",
        "iottwinmaker:DeleteWorkspace",
        "iottwinmaker:CreateComponentType",
        "iottwinmaker:GetComponentType",
        "iottwinmaker:DeleteComponentType",
        "iottwinmaker:ListComponentTypes",
        "iottwinmaker:CreateEntity",
        "iottwinmaker:GetEntity",
        "iottwinmaker:UpdateEntity",
        "iottwinmaker:DeleteEntity",
        "iottwinmaker:ListEntities",
        "iottwinmaker:ListScenes",
        "iottwinmaker:DeleteScene"
      ],
      "Resource": "*"
    },
    {
      "Sid": "GrafanaAndDependencies",
      "Effect": "Allow",
      "Action": [
        "grafana:CreateWorkspace",
        "grafana:DescribeWorkspace",
        "grafana:DeleteWorkspace",
        "grafana:ListWorkspaces",
        "grafana:TagResource",
        "sso:CreateManagedApplicationInstance",
        "sso:DeleteManagedApplicationInstance",
        "sso:DescribeRegisteredRegions",
        "sso:GetSharedSsoConfiguration",
        "organizations:DescribeOrganization",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeSubnets",
        "ec2:GetManagedPrefixListEntries"
      ],
      "Resource": "*"
    },
    {
      "Sid": "StepFunctions",
      "Effect": "Allow",
      "Action": [
        "states:CreateStateMachine",
        "states:DescribeStateMachine",
        "states:DeleteStateMachine"
      ],
      "Resource": "*"
    }
  ]
}
```

## Runtime Role Policies Created by the Application

The permissions above are for the deployment principal. During deployment, the application creates runtime roles and attaches AWS managed or inline policies to those roles. Those runtime policies are not required directly on the deployment principal, except that the principal needs IAM permissions to create and attach them.

Examples of runtime policies attached by the application include:

```text
arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
arn:aws:iam::aws:policy/service-role/AWSLambdaRole
arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess_v2
arn:aws:iam::aws:policy/AWSLambda_ReadOnlyAccess
arn:aws:iam::aws:policy/AWSStepFunctionsFullAccess
arn:aws:iam::aws:policy/AWSIoTDataAccess
arn:aws:iam::aws:policy/AmazonS3FullAccess
```

The Event Registry Register Lambda receives an inline SSM policy for the `/<digitalTwinName>/event-registry` parameter path. The deployment principal does not call SSM directly; it creates that inline runtime policy with `iam:PutRolePolicy`.

## Notes

- `Version: "2012-10-17"` in the JSON policy is the IAM policy language version, not an application version or policy creation date.
- CloudWatch Logs permissions are attached to runtime Lambda roles through `AWSLambdaBasicExecutionRole`; the deployment principal does not call CloudWatch Logs directly.
- If Grafana is removed from Core L5, the Grafana and AWS SSO dependent permissions can be removed from the deployment principal.
- If TwinMaker scene cleanup is removed from `TwinmakerWorkspaceDeployer.destroy`, `iottwinmaker:ListScenes` and `iottwinmaker:DeleteScene` can be removed.
