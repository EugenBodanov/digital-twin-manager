from __future__ import annotations

import unittest
from copy import deepcopy
from unittest.mock import patch

from tests.test_managed_lambda_regressions import ManagedLambdaFixture

import deployment_state
import globals
from deployers.aws.event_actions.lambda_actions import LambdaActionsDeployer


class EventActionCodeChangeTests(ManagedLambdaFixture):
  def setUp(self) -> None:
    super().setUp()
    self.code_path = "microgrid/battery/trigger"
    self.source = self.write_lambda(self.project / self.code_path)
    self.event["action"]["pathToCode"] = self.code_path
    globals.config_events = [self.event]
    deployment_state.last_applied_config_events = deepcopy(globals.config_events)
    self.deployer = LambdaActionsDeployer()

  def test_unchanged_code_is_up_to_date(self) -> None:
    self.deployer.deploy()
    self.single_action(self.deployer.plan(), "NO_CHANGE")

  def test_changed_code_updates_in_place_without_a_saved_hash_file(self) -> None:
    self.deployer.deploy()
    self.change_source(self.source)
    action = self.single_action(self.deployer.plan(), "UPDATE")
    self.deployer.apply(action, action["resource"])
    self.single_action(self.deployer.plan(), "NO_CHANGE")
    self.assertEqual(1, len(self.lambda_client.code_updates))
    self.assertEqual([], self.lambda_client.delete_requests)
    self.assertEqual([], self.iam_client.deleted_roles)

  def test_zip_artifact_in_code_folder_is_ignored(self) -> None:
    self.deployer.deploy()
    self.source.with_name("zipped.zip").write_bytes(b"archive")
    self.single_action(self.deployer.plan(), "NO_CHANGE")

  def test_mapped_folder_is_used_for_deploy_plan_and_apply(self) -> None:
    uploaded = self.write_lambda(self.project / "uploaded")
    uploaded.write_text("print('uploaded release')", encoding="utf-8")
    with patch.dict(globals.event_action_code_paths, {self.code_path: str(uploaded.parent)}):
      self.deployer.deploy()
      self.change_source(self.source)
      self.single_action(self.deployer.plan(), "NO_CHANGE")
      self.change_source(uploaded)
      action = self.single_action(self.deployer.plan(), "UPDATE")
      uploaded.write_text("print('edited after planning')", encoding="utf-8")
      with self.assertRaisesRegex(ValueError, "code changed after planning"):
        self.deployer.apply(action, action["resource"])
      self.assertEqual([], self.lambda_client.code_updates)


if __name__ == "__main__":
  unittest.main()
