from deployers.aws.core.event_checker_iam_role import EventCheckerIamRoleDeployer
from deployers.aws.core.event_checker_lambda_function import EventCheckerLambdaFunctionDeployer
from deployers.aws.core.event_feedback_iam_role import EventFeedbackIamRoleDeployer
from deployers.aws.core.event_feedback_lambda_function import EventFeedbackLambdaFunctionDeployer
from deployers.aws.core.event_registry_register_iam_role import EventRegistryRegisterIamRoleDeployer
from deployers.aws.core.event_registry_register_lambda_function import EventRegistryRegisterLambdaFunctionDeployer
from deployers.aws.core.lambda_chain_iam_role import LambdaChainIamRoleDeployer
from deployers.aws.core.lambda_chain_step_function import LambdaChainStepFunctionDeployer
from deployers.aws.core.persister_iam_role import PersisterIamRoleDeployer
from deployers.aws.core.persister_lambda_function import PersisterLambdaFunctionDeployer
from deployers.aws.core.plan_actions import sort_actions_for_apply
from deployers.base import Deployer

class L2Deployer(Deployer):
  def log(self, message):
    print(message)

  DESTROY_ORDER = {
    "lambda_function": 0,
    "step_function": 1,
    "iam": 2,
  }

  DEPLOY_ORDER = {
    "iam": 0,
    "lambda_function": 1,
    "step_function": 2,
  }

  def plan(self):
    actions = []
    actions.extend(PersisterIamRoleDeployer().plan())
    actions.extend(PersisterLambdaFunctionDeployer().plan())
    actions.extend(EventFeedbackIamRoleDeployer().plan())
    actions.extend(EventFeedbackLambdaFunctionDeployer().plan())
    actions.extend(EventCheckerIamRoleDeployer().plan())
    actions.extend(EventCheckerLambdaFunctionDeployer().plan())
    actions.extend(LambdaChainIamRoleDeployer().plan())
    actions.extend(LambdaChainStepFunctionDeployer().plan())
    actions.extend(EventRegistryRegisterIamRoleDeployer().plan())
    actions.extend(EventRegistryRegisterLambdaFunctionDeployer().plan())
    return {
      "layer": "core_l2",
      "actions": actions,
    }

  def sort_actions_for_apply(self, actions):
    return sort_actions_for_apply(
      actions,
      self.DESTROY_ORDER,
      self.DEPLOY_ORDER,
    )

  def deploy(self):
    PersisterIamRoleDeployer().deploy()
    PersisterLambdaFunctionDeployer().deploy()
    EventFeedbackIamRoleDeployer().deploy()
    EventFeedbackLambdaFunctionDeployer().deploy()
    EventCheckerIamRoleDeployer().deploy()
    EventCheckerLambdaFunctionDeployer().deploy()
    LambdaChainIamRoleDeployer().deploy()
    LambdaChainStepFunctionDeployer().deploy()
    EventRegistryRegisterIamRoleDeployer().deploy()
    EventRegistryRegisterLambdaFunctionDeployer().deploy()

  def destroy(self):
    EventRegistryRegisterLambdaFunctionDeployer().destroy()
    EventRegistryRegisterIamRoleDeployer().destroy()
    LambdaChainStepFunctionDeployer().destroy()
    LambdaChainIamRoleDeployer().destroy()
    EventCheckerLambdaFunctionDeployer().destroy()
    EventCheckerIamRoleDeployer().destroy()
    EventFeedbackLambdaFunctionDeployer().destroy()
    EventFeedbackIamRoleDeployer().destroy()
    PersisterLambdaFunctionDeployer().destroy()
    PersisterIamRoleDeployer().destroy()

  def info(self):
    PersisterIamRoleDeployer().info()
    PersisterLambdaFunctionDeployer().info()
    EventFeedbackIamRoleDeployer().info()
    EventFeedbackLambdaFunctionDeployer().info()
    EventCheckerIamRoleDeployer().info()
    EventCheckerLambdaFunctionDeployer().info()
    LambdaChainIamRoleDeployer().info()
    LambdaChainStepFunctionDeployer().info()
    EventRegistryRegisterIamRoleDeployer().info()
    EventRegistryRegisterLambdaFunctionDeployer().info()
