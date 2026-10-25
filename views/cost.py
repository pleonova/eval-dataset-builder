from result import ModuleResult
from views import render_note


def get_result() -> ModuleResult:
    return ModuleResult(
        name="cost",
        value=None,
        status="na",
        reading="**Coming next:** How many items you need for a target margin, and the expert hours and cost to get there.",
    )


def render() -> None:
    render_note(get_result())
