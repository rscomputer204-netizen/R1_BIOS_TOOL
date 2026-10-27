from .base_brand import BaseBrand


class AsusBrandPlugin(BaseBrand):
    BRAND_NAME = "ASUS"
    SUPPORTED_BRANDS = [
        "ASUS",
        "ASUSTEK",
        "REPUBLIC OF GAMERS",
        "ROG",
    ]

    @classmethod
    def get_ui_buttons(cls, main_window):
        return []

