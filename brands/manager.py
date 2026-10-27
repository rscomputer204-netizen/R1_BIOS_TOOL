import os
import importlib
import inspect
from typing import List, Type
from .base_brand import BaseBrand
from path_utils import get_app_root

class BrandManager:
    _plugins: List[Type[BaseBrand]] = []
    
    @classmethod
    def load_plugins(cls):
        """
        Dynamically loads all python modules in the 'brands' package
        that subclass BaseBrand.
        """
        cls._plugins.clear()
        import pkgutil
        import brands
        
        for loader, module_name, is_pkg in pkgutil.iter_modules(brands.__path__):
            if module_name in ("base_brand", "manager") or module_name.startswith("__"):
                continue
                
            full_module_name = f"brands.{module_name}"
            try:
                module = importlib.import_module(full_module_name)
                # Find all classes that inherit from BaseBrand
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, BaseBrand) and obj is not BaseBrand:
                        if obj not in cls._plugins:
                            cls._plugins.append(obj)
            except Exception as e:
                print(f"[BrandManager] Failed to load plugin {full_module_name}: {e}")
                    
    @classmethod
    def get_plugin_for_brand(cls, dmi_brand: str) -> Type[BaseBrand]:
        """
        Returns the first plugin that supports the given brand string, or None.
        """
        if not cls._plugins:
            cls.load_plugins()
            
        for plugin in cls._plugins:
            if plugin.supports(dmi_brand):
                return plugin
        return None
