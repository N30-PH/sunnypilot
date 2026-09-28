import ast
from pathlib import Path
from types import SimpleNamespace
import pytest


class FakeParams:
  def __init__(self, target=None):
    self.values = {"DisableUpdates": True, "UpdaterTargetBranch": target}
    self.writes = []

  def get(self, key):
    return self.values.get(key)

  def get_bool(self, key):
    return bool(self.get(key))

  def put(self, key, value, *, block):
    assert block and isinstance(value, str)
    self.writes.append(key)
    self.values[key] = value


def load_disabled_path(params):
  # Execute the actual functions with unavailable infrastructure replaced by
  # fail-fast sentinels. No Qt, hardware, updater lock or network is required.
  source = Path(__file__).parents[1] / "updated.py"
  tree = ast.parse(source.read_text())
  selected = [n for n in tree.body if isinstance(n, ast.FunctionDef)
              and n.name in ("refresh_disabled_update_metadata", "main")]

  def stop(code):
    raise SystemExit(code)

  def forbidden(*args, **kwargs):
    raise AssertionError("Disabled updater must not initialize storage or download code")
  metadata = SimpleNamespace(channel="release-tizi", openpilot=SimpleNamespace(version="2026.002.002", git_commit="abcdef1234567890"))
  namespace = {"Params": lambda: params, "get_build_metadata": lambda: metadata,
               "cloudlog": SimpleNamespace(warning=lambda *args: None), "exit": stop, "Updater": forbidden, "open": forbidden}
  exec(compile(ast.Module(body=selected, type_ignores=[]), str(source), "exec"), namespace)
  return namespace


def test_disabled_updater_fills_cleared_fields_and_exits_before_update():
  params = FakeParams()
  namespace = load_disabled_path(params)
  with pytest.raises(SystemExit) as result:
    namespace["main"]()
  assert result.value.code == 0
  assert params.values["UpdaterCurrentDescription"] == "2026.002.002 / release-tizi / abcdef1"
  assert params.values["UpdaterTargetBranch"] == "release-tizi"
  assert params.writes == ["UpdaterCurrentDescription", "UpdaterTargetBranch"]
  assert params.values["DisableUpdates"] is True


@pytest.mark.parametrize("target", ["staging", "custom-channel"])
def test_explicit_target_is_preserved(target):
  params = FakeParams(target)
  load_disabled_path(params)["refresh_disabled_update_metadata"](params)
  assert params.values["UpdaterTargetBranch"] == target
  assert params.writes == ["UpdaterCurrentDescription"]


def test_description_uses_installed_metadata_instead_of_stale_value():
  params = FakeParams()
  params.values["UpdaterCurrentDescription"] = "outdated description"
  load_disabled_path(params)["refresh_disabled_update_metadata"](params)
  assert "outdated" not in params.values["UpdaterCurrentDescription"]
