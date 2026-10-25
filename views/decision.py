from result import ModuleResult
from views import render_card


def get_result() -> ModuleResult:
    return ModuleResult(
        name="decision",
        value=None,
        status="na",
        reading="Coming next: a verdict on which expert labels are safe to tune a judge against.",
    )


def render() -> None:
    render_card(get_result())
