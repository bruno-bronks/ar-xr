"""Logs estruturados: reexporta o formatador compartilhado (REQ-ENG-004)."""

from spatial_common.logging_json import JsonFormatter, configure_logging, correlation_id_var

__all__ = ["JsonFormatter", "configure_logging", "correlation_id_var"]
