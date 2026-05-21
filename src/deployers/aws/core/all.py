from deployers.aws.core.l1 import L1Deployer
from deployers.aws.core.l2 import L2Deployer
from deployers.aws.core.l3_archive import L3ArchiveDeployer
from deployers.aws.core.l3_cold import L3ColdDeployer
from deployers.aws.core.l3_hot import L3HotDeployer
from deployers.aws.core.l4 import L4Deployer
from deployers.aws.core.l5 import L5Deployer
from deployers.aws.apply_actions import ACTION_DEPLOY, ACTION_DESTROY
from deployers.base import Deployer

class AllDeployer(Deployer):
  LAYERS = [
    ("core_l1", L1Deployer),
    ("core_l2", L2Deployer),
    ("core_l3_hot", L3HotDeployer),
    ("core_l3_cold", L3ColdDeployer),
    ("core_l3_archive", L3ArchiveDeployer),
    ("core_l4", L4Deployer),
    ("core_l5", L5Deployer),
  ]

  def log(self, message):
    print(message)

  def plan(self):
    return {
      "group": "core",
      "layers": [
        deployer_class().plan()
        for _, deployer_class in self.LAYERS
      ],
    }

  def apply(self, group_plan, action_name):
    layers_by_name = {
      layer["layer"]: layer
      for layer in group_plan["layers"]
    }
    layer_entries = self.LAYERS

    if action_name == ACTION_DESTROY:
      layer_entries = reversed(layer_entries)
    elif action_name != ACTION_DEPLOY:
      raise ValueError(f"Unsupported apply action: {action_name}")

    for layer_name, deployer_class in layer_entries:
      layer_plan = layers_by_name.get(layer_name)
      if layer_plan is None:
        raise ValueError(f"Missing core plan layer: {layer_name}")

      deployer_class().apply(layer_plan, action_name)

  def deploy(self):
    L1Deployer().deploy()
    L2Deployer().deploy()
    L3HotDeployer().deploy()
    L3ColdDeployer().deploy()
    L3ArchiveDeployer().deploy()
    L4Deployer().deploy()
    L5Deployer().deploy()

  def destroy(self):
    L5Deployer().destroy()
    L4Deployer().destroy()
    L3ArchiveDeployer().destroy()
    L3ColdDeployer().destroy()
    L3HotDeployer().destroy()
    L2Deployer().destroy()
    L1Deployer().destroy()

  def info(self):
    L1Deployer().info()
    L2Deployer().info()
    L3HotDeployer().info()
    L3ColdDeployer().info()
    L3ArchiveDeployer().info()
    L4Deployer().info()
    L5Deployer().info()
