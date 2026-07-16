"""Natural language parsing: free-form text -> canonical action or a free-form request."""

from .parser import Parser, ParseResult

__all__ = ["Parser", "ParseResult"]
