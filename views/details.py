from result import ModuleResult
from views import render_card


def get_result() -> ModuleResult:
    return ModuleResult(
        name="details",
        value=None,
        status="na",
        reading="Coming next: alpha by criterion with grouped ranges, confusion between levels, per-rater kappa.",
    )


def render() -> None:
    render_card(get_result())
