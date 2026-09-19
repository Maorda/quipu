from importlib.metadata import entry_points
from quipu.workspace.base import BaseWorkspaceLayout

def discover_workspace_layout(group_name: str = "quipu.workspace_layouts") -> BaseWorkspaceLayout | None:
    for ep in entry_points(group=group_name):
        try:
            layout_cls = ep.load()
            if issubclass(layout_cls, BaseWorkspaceLayout):
                return layout_cls()
        except Exception:
            continue
    return None