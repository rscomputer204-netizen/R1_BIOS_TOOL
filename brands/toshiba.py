from .base_brand import BaseBrand


class ToshibaBrandPlugin(BaseBrand):
    """
    Toshiba brand plugin.
    Detected by: 'Toshiba', 'Dynabook'

    When Toshiba BIOS is dropped:
      - btn_smart_me_fix -> "TOSHIBA ME CLEAN"
      - btn_extract_dmi  -> "TOSHIBA DMI EX"
    """

    BRAND_NAME = "Toshiba"
    SUPPORTED_BRANDS = [
        "TOSHIBA",
        "DYNABOOK",
    ]

    @classmethod
    def get_ui_buttons(cls, main_window):
        """
        Toshiba-specific sidebar buttons.
        Add Toshiba-specific buttons here when required.
        """
        return []
