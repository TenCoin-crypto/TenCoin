class RPCError(Exception):
    """Base RPC error"""
    pass

class ConnectionError(RPCError):
    """Network connection error"""
    pass

class AuthenticationError(RPCError):
    """Authentication failed"""
    pass

class TimeoutError(RPCError):
    """Request timeout"""
    pass

class ResponseError(RPCError):
    """Invalid response from server"""
    pass

class InvalidMethodError(RPCError):
    """Invalid RPC method"""
    pass