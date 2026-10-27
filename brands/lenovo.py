from .base_brand import BaseBrand


class LenovoBrandPlugin(BaseBrand):
    BRAND_NAME = "Lenovo"
    SUPPORTED_BRANDS = [
        "LENOVO",
        "THINKPAD",
        "IDEAPAD",
        "LEGION",
    ]

    @classmethod
    def get_ui_buttons(cls, main_window):
        return []

