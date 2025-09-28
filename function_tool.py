import inspect
import json
from typing import Any, Dict, Optional, get_type_hints
from functools import wraps

def function_tool(func=None, *, name_override: Optional[str] = None):
    """
    Decorator that converts a function into an OpenAI function tool.
    Extracts function metadata and creates JSON schema for parameters.
    """
    def decorator(f):
        sig = inspect.signature(f)
        doc = inspect.getdoc(f) or ""
        
        description = doc.split('\n')[0].strip() if doc else f.__name__
        
        params_schema = {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        }
        
        type_hints = get_type_hints(f)
        
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
                
            param_type = type_hints.get(param_name, str)
            
            if param_type == str:
                json_type = "string"
            elif param_type == int:
                json_type = "integer"
            elif param_type == float:
                json_type = "number"
            elif param_type == bool:
                json_type = "boolean"
            else:
                json_type = "string"  # Default fallback
            
            params_schema["properties"][param_name] = {
                "type": json_type
            }
            
            params_schema["required"].append(param_name)
        
        @wraps(f)
        async def wrapper(*args, **kwargs):
            return await f(*args, **kwargs)
        
        setattr(wrapper, 'name', name_override or f.__name__)
        setattr(wrapper, 'description', description)
        setattr(wrapper, 'params_json_schema', params_schema)
        setattr(wrapper, 'strict_json_schema', True)
        
        return wrapper
    
    if func is None:
        return decorator
    else:
        return decorator(func)
