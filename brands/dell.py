from .base_brand import BaseBrand


class DellBrandPlugin(BaseBrand):
    SUPPORTED_BRANDS = [
        "DELL",
        "DELL INC.",
        "DELL INC",
        "ALIENWARE",
    ]

    @classmethod
    def get_ui_buttons(cls, main_window):
        return []

