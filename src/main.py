import globals
import deployers.aws.core.all
import deployers.aws.iot.all
import deployers.aws.hierarchy.all
import deployers.aws.event_actions.all
import deployers.aws.init_values.all
import deployers.aws.all
import deployment_state
import sanity_checker

def help_menu():
  print("""
    Available commands:
      deploy                       - Deploys core and IoT services and resources.
      destroy                      - Destroys core and IoT services and resources.
      info                         - Lists all the deployed resources.
      plan                         - Plans core resource changes without modifying AWS.
      apply                        - Loads and sorts saved plan actions for apply.
      init-state                   - Copies current deploy config files into redeployment state.
      help                         - Show this help menu.
      exit                         - Exit the program.
  """)


def _print_missing_state_help(error):
  print(error)
  print(
    "Start with 'init-state' if the AWS resources already exist, "
    "or 'deploy' if this is a fresh deployment."
  )


def _try_initialize_last_applied_config_state():
  try:
    deployment_state.initialize_last_applied_config_state()
    return True
  except FileNotFoundError as error:
    _print_missing_state_help(error)
    return False


def main():
    globals.initialize_config()
    globals.initialize_config_iot_devices()
    globals.initialize_config_credentials()
    globals.initialize_config_events()
    globals.initialize_config_hierarchy()
    globals.initialize_aws_iam_client()
    globals.initialize_aws_lambda_client()
    globals.initialize_aws_iot_client()
    globals.initialize_aws_sts_client()
    globals.initialize_aws_events_client()
    globals.initialize_aws_dynamodb_client()
    globals.initialize_aws_s3_client()
    globals.initialize_aws_twinmaker_client()
    globals.initialize_aws_grafana_client()
    globals.initialize_aws_logs_client()
    globals.initialize_aws_sf_client()
    globals.initialize_aws_iot_data_client()
    _try_initialize_last_applied_config_state()

    print("Welcome to the Digital Twin Manager. Type 'help' for commands.")

    while True:
      try:
        user_input = input(">>> ").strip()
      except (EOFError, KeyboardInterrupt):
        print("Goodbye!")
        break

      if not user_input:
        continue

      parts = user_input.split()
      command = parts[0]
      args = parts[1:]

      if command == "deploy":
        sanity_checker.check()
        deployers.aws.core.all.AllDeployer().deploy()
        deployers.aws.iot.all.AllDeployer().deploy()
        deployers.aws.hierarchy.all.AllDeployer().deploy()
        deployers.aws.event_actions.all.AllDeployer().deploy()
        deployers.aws.init_values.all.AllDeployer().deploy()
        deployment_state.save_last_applied_config_state()
        print(f"State configs saved to: {deployment_state.state_config_dir_path()}")

      elif command == "destroy":
        deployers.aws.init_values.all.AllDeployer().destroy()
        deployers.aws.event_actions.all.AllDeployer().destroy()
        deployers.aws.hierarchy.all.AllDeployer().destroy()
        deployers.aws.iot.all.AllDeployer().destroy()
        deployers.aws.core.all.AllDeployer().destroy()

      elif command == "info":
        deployers.aws.core.all.AllDeployer().info()
        deployers.aws.iot.all.AllDeployer().info()
        deployers.aws.hierarchy.all.AllDeployer().info()
        deployers.aws.event_actions.all.AllDeployer().info()
        deployers.aws.init_values.all.AllDeployer().info()

      elif command == "plan":
        sanity_checker.check()
        if not _try_initialize_last_applied_config_state():
          continue

        plan_groups = [deployers.aws.core.all.AllDeployer().plan(), deployers.aws.iot.all.AllDeployer().plan(),
                       deployers.aws.hierarchy.all.AllDeployer().plan(),
                       deployers.aws.event_actions.all.AllDeployer().plan(),
                       deployers.aws.init_values.all.AllDeployer().plan()]

        plan_path = deployment_state.save_plan(plan_groups)
        print(f"Plan saved to: {plan_path}")

      elif command == "apply":
        if not _try_initialize_last_applied_config_state():
          continue

        plan = deployment_state.load_plan()

        if not plan:
          print("No saved plan found. Run 'plan' first.")
          continue

        print(f"Loaded plan from: {deployment_state.state_plan_file_path()}")
        deployers.aws.all.AllDeployer().apply(plan)
        deployment_state.save_last_applied_config_state()
        print(f"State configs saved to: {deployment_state.state_config_dir_path()}")
        

      elif command == "init-state":
        sanity_checker.check()
        deployment_state.save_last_applied_config_state()
        print(f"Redeployment state configs saved to: {deployment_state.state_config_dir_path()}")

      elif command == "help":
        help_menu()

      elif command == "exit":
        print("Goodbye!")
        break

      else:
        print(f"Unknown command: {command}. Type 'help' for a list of commands.")

if __name__ == "__main__":
  main()
