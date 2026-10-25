from result import ModuleResult
from views import render_card


def get_result() -> ModuleResult:
    return ModuleResult(
        name="precheck",
        value=None,
        status="na",
        reading="Coming next: an AI dry run that flags unclear rubric wording before experts rate.",
    )


def render() -> None:
    render_card(get_result())
