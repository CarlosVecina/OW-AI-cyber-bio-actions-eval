from pydantic import BaseModel, Field
from typing import Callable, Dict, Any, Optional
import inspect


class LLMTool(BaseModel):
    """
    A Pydantic class for LLM tools that can be called as a function
    and provides a method to get the tool description in OpenAI format.
    """
    
    name: str = Field(..., description="The name of the tool/function")
    description: str = Field(..., description="Description of what the tool does")
    parameters: Dict[str, Any] = Field(..., description="JSON schema for function parameters")
    function: Optional[Callable] = Field(None, description="Optional callable function to execute")
    
    def __call__(self, **kwargs) -> Any:
        """
        Call the tool as a function.
        
        Args:
            **kwargs: Arguments to pass to the function
            
        Returns:
            Result of calling the function
        """
        if self.function is None:
            raise ValueError(f"Tool '{self.name}' has no function implementation")
        
        # Validate required parameters
        required = self.parameters.get("required", [])
        missing = [param for param in required if param not in kwargs]
        if missing:
            raise ValueError(f"Missing required parameters: {missing}")
        
        return self.function(**kwargs)
    
    def get_tool_description(self) -> Dict[str, Any]:
        """
        Get the tool description in OpenAI-compatible format.
        
        Returns:
            Dictionary in OpenAI tool format:
            {
                "type": "function",
                "function": {
                    "name": "...",
                    "description": "...",
                    "parameters": {...}
                }
            }
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }
    
    @classmethod
    def from_function(
        cls,
        func: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> "LLMTool":
        """
        Create an LLMTool from a Python function using introspection.
        
        Args:
            func: The function to convert to a tool
            name: Optional name (defaults to function name)
            description: Optional description (defaults to function docstring)
            
        Returns:
            LLMTool instance
        """
        sig = inspect.signature(func)
        name = name or func.__name__
        description = description or (func.__doc__ or "").strip()
        
        properties = {}
        required = []
        
        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue
                
            param_info = {
                "type": "string"  # default
            }
            
            if param.annotation != inspect.Parameter.empty:
                type_map = {
                    str: "string",
                    int: "integer",
                    float: "number",
                    bool: "boolean",
                    list: "array",
                    dict: "object"
                }
                param_info["type"] = type_map.get(param.annotation, "string")
            
            if param.default != inspect.Parameter.empty:
                param_info["default"] = param.default
            else:
                required.append(param_name)
            
            if param.annotation != inspect.Parameter.empty and param.annotation == list:
                param_info["items"] = {"type": "string"}
            
            properties[param_name] = param_info
        
        parameters = {
            "type": "object",
            "properties": properties
        }
        
        if required:
            parameters["required"] = required
        
        return cls(
            name=name,
            description=description,
            parameters=parameters,
            function=func
        )