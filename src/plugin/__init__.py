import importlib
import logging
import os
import pkgutil

logger = logging.getLogger(__name__)


def discover_plugins():
    """Discover all valid plugins under the ``plugin`` package.

    Each subdirectory of ``src/plugin/`` that contains an ``__init__.py``
    with a module-level ``register(mainwindow)`` callable is considered a
    plugin.

    Returns:
        list[dict]: A list of plugin info dicts, each with keys:
            - ``name``     (str):      Human-readable plugin name (falls back
                                       to the module name).
            - ``register`` (callable): The ``register(mainwindow)`` function.
    """
    plugins = []
    package_dir = os.path.dirname(__file__)

    for finder, name, ispkg in pkgutil.iter_modules([package_dir]):
        if not ispkg:
            continue

        module_name = f'plugin.{name}'
        try:
            mod = importlib.import_module(module_name)
        except Exception:
            logger.exception('Failed to import plugin %r — skipping.', name)
            continue

        register_fn = getattr(mod, 'register', None)
        if not callable(register_fn):
            logger.debug(
                'Plugin %r has no callable register() — skipping.', name
            )
            continue

        display_name = getattr(mod, 'PLUGIN_NAME', name)
        plugins.append({'name': display_name, 'register': register_fn})
        logger.info('Discovered plugin: %s', display_name)

    return plugins
