import json


def normalized_json(value):
  return json.dumps(value, sort_keys=True)
