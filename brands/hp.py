from .base_brand import BaseBrand


class HPBrandPlugin(BaseBrand):
    SUPPORTED_BRANDS = ["HP", "HEWLETT-PACKARD", "HEWLETT PACKARD", "COMPAQ"]
    
    @classmethod
    def get_ui_buttons(cls, main_window):
        return []

