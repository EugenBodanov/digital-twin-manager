from deployers.aws.iot.l1 import L1Deployer
from deployers.aws.iot.l2 import L2Deployer
from deployers.aws.iot.l4 import L4Deployer
from deployers.aws.apply_actions import ACTION_DEPLOY, ACTION_DESTROY
from deployers.base import Deployer

class AllDeployer(Deployer):
  LAYERS = [
    ("iot_l1", L1Deployer),
    ("iot_l2", L2Deployer),
    ("iot_l4", L4Deployer),
  ]

  def log(self, message):
    print(f"IoT: {message}")
  
  def plan(self):
    return {
      "group": "iot",
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
        raise ValueError(f"Missing IoT plan layer: {layer_name}")

      deployer_class().apply(layer_plan, action_name)


  def deploy(self):
    L1Deployer().deploy()
    L2Deployer().deploy()
    L4Deployer().deploy()

  def destroy(self):
    L4Deployer().destroy()
    L2Deployer().destroy()
    L1Deployer().destroy()

  def info(self):
    L1Deployer().info()
    L2Deployer().info()
    L4Deployer().info()
