class CanopyError(Exception):
    pass


class ConfigError(CanopyError):
    pass


class CollectorError(CanopyError):
    pass


class LayoutError(CanopyError):
    pass


class RenderError(CanopyError):
    pass
