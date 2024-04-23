import importlib
import pkgutil
import inspect

from .prompt import BasePrompt, LegacyPrompt


def load_prompts(package):
    plugins = {}
    # 遍历给定包中的所有模块
    for _, module_name, _ in pkgutil.iter_modules(package.__path__, package.__name__ + '.'):
        # 导入模块
        module = importlib.import_module(module_name)
        # 遍历模块中的所有类
        for name, obj in inspect.getmembers(module, inspect.isclass):
            # 检查这个类是否继承自PluginInterface
            if issubclass(obj, BasePrompt) and obj is LegacyPrompt:
                plugins[0] = obj
                plugins[1] = obj
                plugins[2] = obj
                plugins[3] = obj
                plugins[4] = obj
                plugins[5] = obj
                plugins[6] = obj
                plugins[7] = obj
                plugins[8] = obj
            elif issubclass(obj, BasePrompt) and obj is not BasePrompt:
                plugins[obj.name()] = obj
    return plugins
