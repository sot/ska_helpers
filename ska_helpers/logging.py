# Licensed under a 3-clause BSD style license - see LICENSE.rst

__all__ = ["basic_logger"]


def basic_logger(name, format="%(asctime)s %(funcName)s: %(message)s", **kwargs):
    """Create logger ``name`` using logging.basicConfig.

    This is a thin wrapper around logging.basicConfig, except:

    - Uses logger named ``name`` instead of the root logger
    - Defaults to a standard format for Ska applications. Specify
      ``format=None`` to use the default ``basicConfig`` format.
    - Not recommended for multithreaded or multiprocess applications due to
      using a temporary monkey-patch of a global variable to create the logger.
      It will probably work but it is not guaranteed.

    This function does nothing if the ``name`` logger already has handlers
    configured, unless the keyword argument *force* is set to ``True``.
    It is a convenience method intended to do one-shot creation of a logger.

    The default behaviour is to create a StreamHandler which writes to
    ``sys.stderr``, set a formatter using the format string ``"%(asctime)s
    %(funcName)s: %(message)s"``, and add the handler to the ``name`` logger
    with a level of WARNING.

    Example::

      # In __init__.py for a package or in any module
      from ska_helpers.logging import basic_logger
      logger = basic_logger(__name__, level='INFO')

      # In other submodules within a package the normal usage is to inherit
      # the package logger.
      import logging
      logger = logging.getLogger(__name__)

    A number of optional keyword arguments may be specified, which can alter
    the default behaviour.

    filename  Specifies that a FileHandler be created, using the specified
              filename, rather than a StreamHandler.

    filemode  Specifies the mode to open the file, if filename is specified
              (if filemode is unspecified, it defaults to 'a').

    format    Use the specified format string for the handler.

    datefmt   Use the specified date/time format.

    style     If a format string is specified, use this to specify the
              type of format string (possible values '%', '{', '$', for
              %-formatting, :meth:`str.format` and :class:`string.Template`
              - defaults to '%').

    level     Set the ``name`` logger level to the specified level. This can be
              a number (10, 20, ...) or a string ('NOTSET', 'DEBUG', 'INFO',
              'WARNING', 'ERROR', 'CRITICAL') or ``logging.DEBUG``, etc.

    stream    Use the specified stream to initialize the StreamHandler. Note
              that this argument is incompatible with 'filename' - if both
              are present, 'stream' is ignored.

    handlers  If specified, this should be an iterable of already created
              handlers, which will be added to the ``name`` handler. Any handler
              in the list which does not have a formatter assigned will be
              assigned the formatter created in this function.

    force     If this keyword  is specified as true, any existing handlers
              attached to the ``name`` logger are removed and closed, before
              carrying out the configuration as specified by the other
              arguments.

    Note that you could specify a stream created using open(filename, mode)
    rather than passing the filename and mode in. However, it should be
    remembered that StreamHandler does not close its stream (since it may be
    using sys.stdout or sys.stderr), whereas FileHandler closes its stream
    when the handler is closed.

    Note this function is probably not thread-safe.

    Parameters
    ----------
    name : str
        logger name
    format : str
        format string for handler
    **kwargs : dict
        other keyword arguments for logging.basicConfig

    Returns
    -------
    logger : Logger object
    """
    import logging

    if format is not None:
        kwargs["format"] = format
    logger = logging.getLogger(name)

    if not kwargs.get("force", False) and (
        logger.hasHandlers() or logger.level != logging.NOTSET
    ):
        return logger

    # Monkeypatch logging temporarily and configure our logger
    root = logging.root
    try:
        logging.root = logger
        logging.basicConfig(**kwargs)
    finally:
        logging.root = root

    return logger
