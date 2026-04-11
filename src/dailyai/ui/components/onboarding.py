from nicegui import ui

from dailyai.ui.components.theme import COLORS
from dailyai.ui.i18n import tr


class OnboardingState:
    def __init__(self):
        self.step = 1


def onboarding_dialog(language: str, sync_code: str):
    """Shows an onboarding dialog sequence for first-time users.
    Returns the Dialog instance which you can .open() on demand.
    """

    with (
        ui.dialog().classes("backdrop-blur-sm").props("persistent") as dialog,
        ui.card()
        .classes("w-full max-w-sm shrink shadow-2xl p-0 overflow-hidden relative")
        .style(f"background: {COLORS['bg_card']}; border: 1px solid {COLORS['border']}"),
    ):
        # Step state
        app_step = OnboardingState()

        def next_step(val):
            app_step.step = val

        # Content containers
        with (
            ui.column()
            .classes("p-6 w-full items-center text-center")
            .bind_visibility_from(app_step, "step", lambda s: s == 1)
        ):
            ui.icon("auto_awesome", size="4rem").classes("mb-2").style(f"color: {COLORS['accent']}")
            ui.label(tr(language, "onboarding_welcome_title")).classes(
                "text-2xl font-bold tracking-tight"
            ).style(f"color: {COLORS['text_primary']}")
            ui.label(tr(language, "onboarding_welcome_text")).classes("text-base mt-2").style(
                f"color: {COLORS['text_secondary']}"
            )
            ui.button(tr(language, "onboarding_next"), on_click=lambda: next_step(2)).classes(
                "w-full mt-6 rounded-xl font-bold py-3 text-lg"
            ).style(f"background: {COLORS['accent']}; color: {COLORS['bg_primary']}")

        with (
            ui.column()
            .classes("p-6 w-full items-center text-center")
            .bind_visibility_from(app_step, "step", lambda s: s == 2)
        ):
            ui.icon("view_carousel", size="4rem").classes("mb-2").style(
                f"color: {COLORS['accent_teal']}"
            )
            ui.label(tr(language, "onboarding_swipe_title")).classes(
                "text-2xl font-bold tracking-tight"
            ).style(f"color: {COLORS['text_primary']}")
            ui.label(tr(language, "onboarding_swipe_text")).classes("text-base mt-2").style(
                f"color: {COLORS['text_secondary']}"
            )
            ui.button(tr(language, "onboarding_next"), on_click=lambda: next_step(3)).classes(
                "w-full mt-6 rounded-xl font-bold py-3 text-lg"
            ).style(f"background: {COLORS['accent_teal']}; color: {COLORS['bg_primary']}")

        with (
            ui.column()
            .classes("p-6 w-full items-center text-center")
            .bind_visibility_from(app_step, "step", lambda s: s == 3)
        ):
            ui.icon("sync", size="4rem").classes("mb-2").style(f"color: {COLORS['accent_alt']}")
            ui.label(tr(language, "onboarding_sync_title")).classes(
                "text-2xl font-bold tracking-tight"
            ).style(f"color: {COLORS['text_primary']}")
            ui.label(tr(language, "onboarding_sync_text")).classes("text-base mt-2").style(
                f"color: {COLORS['text_secondary']}"
            )

            # Show the generated code
            ui.label(sync_code).classes(
                "text-xl font-mono font-bold mt-4 px-4 py-2 rounded-lg bg-black/40 border tracking-widest"
            ).style(f"color: {COLORS['accent']}; border-color: {COLORS['border']}")

            ui.button(tr(language, "onboarding_start_button"), on_click=dialog.close).classes(
                "w-full mt-6 rounded-xl font-bold py-3 text-lg"
            ).style(f"background: {COLORS['accent_alt']}; color: {COLORS['bg_primary']}")

    return dialog
