import json


def load_terraform_plan(file_path):
    """
    Load the Terraform plan JSON from a file.
    :param file_path: Terraform plan JSON file
    :return: Dictionary of Terraform plan objects
    """
    with open(file_path, 'r') as file:
        return json.load(file)


def change_details(change, action):
    """
    The change details of a terraform plan.
    :param change: Change object
    :param action: The type of action {"create", "delete", "update", "replace", "no-op"}
    :return: Restructured object for analysis
    """
    control_actions = ["create", "delete", "update", "replace"]
    resource_name = change.get("name")
    resource_type = change.get("type")
    resource_actions = change.get("change", {}).get("actions", [])
    if action[0] in control_actions:
        resource_before = change.get("change", {}).get("before", {})
        resource_after = change.get("change", {}).get("after", {})
        resource = {
            "name": resource_name,
            "type": resource_type,
            "actions": resource_actions,
            "before": resource_before if resource_before else {},
            "after": resource_after if resource_after else {},
            "dependencies": change.get("change", {}).get("dependencies", {}),
            "differences": get_the_differences(resource_before, resource_after)
        }
    else:
        resource = {
            "name": resource_name,
            "type": resource_type,
            "actions": resource_actions,
            "before": {},
            "after": {},
            "dependencies": change.get("change", {}).get("dependencies", {}),
            "differences": {}
        }
    return resource


def analyse_plan(plan, type_of_change):
    """
    Analyse the Terraform plan and retrieve detailed resource information, and summary of totals.
    :param plan: Terraform plan Dictionary
    :param type_of_change: type of change to extract data from ["resource_drift", "resource_changes"]
    :return: Tuple of changes_dict containing key for change types and related changes,
             and summary of all changes related to section taken from the Terraform Plan Dictionary
    """
    changes = plan.get(type_of_change, [])

    summary = {
        "create": 0,
        "update": 0,
        "delete": 0,
        "replace": 0,
        "no_op": 0,
    }

    changes_dict = {
        "create_and_delete": [],
        "create": [],
        "update": [],
        "delete": [],
        "replace": [],
        "no_op": [],
    }

    if not changes:
        return None  # No changes detected

    for change in changes:
        action = change.get("change", {}).get("actions", [])
        if "create" in action:
            summary["create"] += 1
            if "delete" in action:
                changes_dict["create_and_delete"].append(change_details(change, action))
            else:
                changes_dict["create"].append(change_details(change, action))
        if "update" in action:
            summary["update"] += 1
            changes_dict["update"].append(change_details(change, action))
        if "delete" in action:
            summary["delete"] += 1
            if "create" not in action:
                changes_dict["delete"].append(change_details(change, action))
        if "replace" in action:
            summary["replace"] += 1
            changes_dict["replace"].append(change_details(change, action))
        if "no-op" in action:
            summary["no_op"] += 1
            changes_dict["no_op"].append(change_details(change, action))

    return changes_dict, summary


def display_detailed_changes(detailed_changes, type_of_change):
    """
    Display the detailed changes of the Terraform plan analysis in Terminal.
    :param detailed_changes: The classified dictionary of changes coming from analyse_plan(plan, change_type) function
    :param type_of_change:  type of change to extract data from ["resource_drift", "resource_changes"]
    :return: None
    """
    print(f"Detailed Terraform Plan Analysis: +++({type_of_change})+++")
    for change_type, change_value in detailed_changes.items():

        if change_value is None:
            print(f"No changes detected in the Terraform plan for the +++({change_type})+++ section")
        else:
            print(f"Detailed Terraform Plan Analysis  for the +++({change_type})+++ section:")
            for change in change_value:
                resource_name = change.get("name")
                resource_type = change.get("type")
                resource_before = change.get('before')
                resource_after = change.get('after')
                resource_dependencies = change.get('dependencies')
                resource_differences = change.get('differences')

                print(f"\nResource Name: {resource_name}")
                print(f"Resource Type: {resource_type}")
                print(f"Actions: {', '.join(change['actions'])}")
                print("Before:")
                print(json.dumps(resource_before, indent=4))
                print("After:")
                print(json.dumps(resource_after, indent=4))
                print("Dependencies:")
                print(json.dumps(resource_dependencies, indent=4))
                print("Differences:")
                print(json.dumps(resource_differences, indent=4))


def display_summary(summary, type_of_change):
    """
    Display the summary of the Terraform plan analysis in Terminal.
    :param summary: The summary of changes coming from analyse_plan(plan, change_type) function
    :param type_of_change: type of change to extract data from ["resource_drift", "resource_changes"]
    :return: None
    """
    print(f"Terraform Plan Summary: +++{type_of_change}+++")
    print(f"Resources to create: {summary['create']}")
    print(f"Resources to update: {summary['update']}")
    print(f"Resources to delete: {summary['delete']}")
    print(f"Resources to replace: {summary['replace']}")
    print(f"Resources with no operation: {summary['no_op']}")


def find_differences(before, after, path=""):
    """
    Find the differences between the before and after state of a terraform plan changes.
    :param before: Dictionary of before variables values
    :param after: Dictionary of after variables values
    :return: differences Dictionary of changes between before and after whether it was added, removed or updated/changed
    """
    differences = {
        "added": {},
        "removed": {},
        "changed": {}
    }

    # Compare dictionaries
    if isinstance(before, dict) and isinstance(after, dict):
        before_keys = set(before.keys())
        after_keys = set(after.keys())

        for key in after_keys - before_keys:
            differences["added"][f"{path}.{key}".strip(".")] = after[key]

        for key in before_keys - after_keys:
            differences["removed"][f"{path}.{key}".strip(".")] = before[key]

        for key in before_keys & after_keys:
            sub_diff = find_differences(before[key], after[key], path=f"{path}.{key}".strip("."))
            differences["added"].update(sub_diff["added"])
            differences["removed"].update(sub_diff["removed"])
            differences["changed"].update(sub_diff["changed"])

    # Compare lists
    elif isinstance(before, list) and isinstance(after, list):
        for i, (b_item, a_item) in enumerate(zip(before, after)):
            sub_diff = find_differences(b_item, a_item, path=f"{path}[{i}]")
            differences["added"].update(sub_diff["added"])
            differences["removed"].update(sub_diff["removed"])
            differences["changed"].update(sub_diff["changed"])

        # Handle added or removed items in lists
        if len(after) > len(before):
            for i in range(len(before), len(after)):
                differences["added"][f"{path}[{i}]".strip(".")] = after[i]
        elif len(before) > len(after):
            for i in range(len(after), len(before)):
                differences["removed"][f"{path}[{i}]".strip(".")] = before[i]

    # Compare values directly
    else:
        if before != after:
            differences["changed"][path] = {
                "before": before,
                "after": after
            }

    return differences


def get_the_differences(before, after):
    differences = find_differences(before, after)

    if differences["added"] or differences["removed"] or differences["changed"]:
        return differences


def generate_json_files(changes, type_of_change):
    """
    Output all the changes in their relative json files.
    :param changes: The classified dictionary of changes coming from analyse_plan(plan, change_type) function
    :param type_of_change: type of change to extract data from ["resource_drift", "resource_changes"]
    :return:
    """
    for change_type, change_value in changes.items():
        with open(f"outputs/{change_type}_{type_of_change}.json", "w") as file:
            json.dump(change_value, file)


def main():
    change_types = ["resource_drift", "resource_changes"]
    # Path to the Terraform plan JSON file
    file_path = 'terraform_plan.json'
    for change_type in change_types:
        # Load the Terraform plan
        plan = load_terraform_plan(file_path)

        # Analyze the plan
        detailed_changes, summary = analyse_plan(plan, change_type)

        # Display the analysis summary
        display_summary(summary, change_type)
        display_detailed_changes(detailed_changes, change_type)
        generate_json_files(detailed_changes, change_type)


if __name__ == "__main__":
    main()
