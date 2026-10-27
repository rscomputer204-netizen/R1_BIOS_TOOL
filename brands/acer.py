from .base_brand import BaseBrand


class AcerBrandPlugin(BaseBrand):
    BRAND_NAME = "Acer"
    SUPPORTED_BRANDS = [
        "ACER",
        "PREDATOR",
        "PACKARD BELL",
        "GATEWAY",
    ]

    @classmethod
    def get_ui_buttons(cls, main_window):
        return []

