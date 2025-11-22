from typing import Dict, Optional, List
from .base_tool import LLMTool


class ToolRepository:
    """
    A simple repository for storing and retrieving LLM tools by name.
    """
    
    def __init__(self):
        self._tools: Dict[str, dict[str, LLMTool]] = {}
    
    def register(self, key: str, tool: LLMTool) -> None:
        """
        Register a tool in the repository.
        
        Args:
            tool: The LLMTool instance to register
            
        Raises:
            ValueError: If a tool with the same name already exists for the given key
        """
        if key not in self._tools:
            self._tools[key] = {}
        if tool.name in self._tools[key]:
            raise ValueError(f"Tool '{tool.name}' is already registered for key '{key}'")

        self._tools[key][tool.name] = tool
    
    def register_many(self, key: str, tools: List[LLMTool]) -> None:
        """
        Register multiple tools at once.
        
        Args:
            tools: List of LLMTool instances to register
            key: The key to register the tools under for the given key
        """
        for tool in tools:
            self.register(key, tool)
    
    def get(self, key: str, name: str) -> Optional[LLMTool]:
        """
        Get a tool by name.
        
        Args:
            name: The name of the tool to retrieve
            
        Returns:
            The LLMTool instance, or None if not found
        """
        return self._tools.get(key).get(name)
    
    def get_or_raise(self, key: str, name: str) -> LLMTool:
        """
        Get a tool by name, raising an error if not found.
        
        Args:
            name: The name of the tool to retrieve
            
        Returns:
            The LLMTool instance
            
        Raises:
            KeyError: If the tool is not found
        """
        if name not in self._tools[key]:
            raise KeyError(f"Tool '{name}' not found in repository. Available tools: {list(self._tools.keys())}")
        return self._tools[key][name]
    
    def list_tools(self, key: str) -> List[str]:
        """
        Get a list of all registered tool names.
        
        Returns:
            List of tool names
        """
        return list(self._tools[key].keys())
    
    def get_tool_descriptions(self, key: str, tool_names: Optional[List[str]] = None) -> List[Dict]:
        """
        Get OpenAI-compatible tool descriptions for registered tools.
        
        Args:
            tool_names: Optional list of tool names to filter by. If None, returns all tools.
            
        Returns:
            List of tool description dictionaries
            
        Raises:
            KeyError: If any tool name in tool_names is not found in the repository
        """
        if tool_names is None:
            return [tool.get_tool_description() for tool in self._tools[key].values()]
        
        # Filter to only requested tools
        missing_tools = [name for name in tool_names if name not in self._tools[key]]
        if missing_tools:
            raise KeyError(
                f"Tools not found in repository: {missing_tools}. "
                f"Available tools: {list(self._tools[key].keys())}"
            )
        
        return [self._tools[key][name].get_tool_description() for name in tool_names]

    def get_all_tool_descriptions(self) -> List[Dict]:
        """
        Get all tool descriptions for all tools in the repository.
        
        Returns:
            List of tool description dictionaries
        """
        return [self.get_tool_descriptions(key) for key in self._tools.keys()]
    
    def unregister(self, name: str) -> None:
        """
        Unregister a tool from the repository.
        
        Args:
            name: The name of the tool to unregister
            
        Raises:
            KeyError: If the tool is not found
        """
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found in repository")
        del self._tools[name]
    
    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()
    
    def __contains__(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools
    
    def __len__(self) -> int:
        """Get the number of registered tools."""
        return len(self._tools)


# Global repository instance
_default_repository = ToolRepository()


def get_repository() -> ToolRepository:
    """
    Get the default global tool repository.
    
    Returns:
        The default ToolRepository instance
    """
    return _default_repository


def register_tool(key: str, tool: LLMTool) -> None:
    """
    Register a tool in the default repository.
    
    Args:
        tool: The LLMTool instance to register
    """
    _default_repository.register(key, tool)


def get_tool(name: str) -> Optional[LLMTool]:
    """
    Get a tool by name from the default repository.
    
    Args:
        name: The name of the tool to retrieve
        
    Returns:
        The LLMTool instance, or None if not found
    """
    return _default_repository.get(name)