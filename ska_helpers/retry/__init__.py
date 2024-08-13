"""
Retry package initially copied from https://github.com/invl/retry.

This project appears to be abandoned so moving it to ska_helpers.

LICENSE::

    Copyright 2014 invl

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""

__all__ = ["retry", "retry_call", "RetryError", "tables_open_file"]

import logging
from logging import StreamHandler

from .api import RetryError, retry, retry_call, tables_open_file

log = logging.getLogger(__name__)
log.addHandler(StreamHandler())
