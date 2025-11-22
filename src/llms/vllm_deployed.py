import requests
from typing import Dict, Any, Union, List, Optional

try:
    from vllm import LLM, SamplingParams
    VLLM_AVAILABLE = True
except ImportError:
    VLLM_AVAILABLE = False
    LLM = object  # Fallback for type checking
    SamplingParams = None


class RequestOutput:
    """Simple wrapper to mimic vLLM's RequestOutput structure."""
    def __init__(self, text: str):
        class Output:
            def __init__(self, text: str):
                self.text = text
        self.outputs = [Output(text)]


class LocalVLLM(LLM):
    """
    A class that inherits from vLLM's LLM and connects to a locally deployed
    vLLM model via HTTP API, providing a generate interface with model parameters.
    
    This class uses the OpenAI-compatible API endpoint provided by vLLM's
    API server to generate text from prompts while maintaining compatibility
    with vLLM's LLM interface.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: Optional[float] = None,
        **kwargs
    ):
        """
        Initialize the LocalVLLM client.
        
        Args:
            base_url: Base URL of the locally deployed vLLM API server
            api_key: API key for authentication (optional, usually not needed for local)
            timeout: Request timeout in seconds
            **kwargs: Additional arguments (ignored, kept for compatibility with LLM.__init__)
        """
        # Don't call super().__init__() to avoid loading a model
        # Instead, set up HTTP client
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.completions_endpoint = f"{self.base_url}/v1/completions"
    
    def _prepare_request_params(
        self,
        prompt: str,
        model_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Prepare request parameters for the API call.
        
        Args:
            prompt: The prompt string
            model_params: Dictionary of model parameters
        
        Returns:
            Dictionary of parameters for the API request
        """
        params = {"prompt": prompt}
        
        if model_params:
            # Handle parameter name mapping
            params.update(model_params.copy())
            
            # Map common parameter names
            if "max_new_tokens" in params:
                params["max_tokens"] = params.pop("max_new_tokens")
            elif "max_length" in params and "max_tokens" not in params:
                params["max_tokens"] = params.pop("max_length")
            
            # Remove parameters that don't apply to the API
            params.pop("input_ids", None)
            params.pop("attention_mask", None)
        
        return params
    
    def generate(
        self,
        prompts: Union[str, List[str]],
        sampling_params: Optional[Union[SamplingParams, Dict[str, Any]]] = None,
        **kwargs
    ) -> List[RequestOutput]:
        """
        Generate text from prompts using sampling parameters.
        
        This method overrides vLLM's generate to use HTTP requests while
        maintaining the same interface and return format.
        
        Args:
            prompts: Single prompt string or list of prompt strings
            sampling_params: SamplingParams object or dict of parameters (e.g., {"max_tokens": 100, "temperature": 0.7})
            **kwargs: Additional arguments (for compatibility)
        
        Returns:
            List of RequestOutput objects (compatible with vLLM's return format)
        
        Examples:
            >>> from vllm import SamplingParams
            >>> model = LocalVLLM()
            >>> outputs = model.generate(
            ...     "Write a short story about AI.",
            ...     sampling_params=SamplingParams(max_tokens=100, temperature=0.7)
            ... )
            >>> print(outputs[0].outputs[0].text)
            
            >>> # Or with dict
            >>> outputs = model.generate(
            ...     "Hello!",
            ...     sampling_params={"max_tokens": 50, "temperature": 0.7}
            ... )
        """
        # Convert single prompt to list for uniform processing
        if isinstance(prompts, str):
            prompts = [prompts]
        
        # Convert sampling_params to dict if it's a SamplingParams object
        model_params = None
        if sampling_params is not None:
            if isinstance(sampling_params, SamplingParams):
                # Convert SamplingParams to dict
                model_params = {
                    "max_tokens": getattr(sampling_params, "max_tokens", None),
                    "temperature": getattr(sampling_params, "temperature", None),
                    "top_p": getattr(sampling_params, "top_p", None),
                    "top_k": getattr(sampling_params, "top_k", None),
                    "stop": getattr(sampling_params, "stop", None),
                    "presence_penalty": getattr(sampling_params, "presence_penalty", None),
                    "frequency_penalty": getattr(sampling_params, "frequency_penalty", None),
                }
                # Remove None values
                model_params = {k: v for k, v in model_params.items() if v is not None}
            elif isinstance(sampling_params, dict):
                model_params = sampling_params
        
        results = []
        for prompt in prompts:
            request_params = self._prepare_request_params(prompt, model_params)
            
            # Prepare headers
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            # Make the API request
            response = requests.post(
                self.completions_endpoint,
                json=request_params,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Extract text from API response
            response_json = response.json()
            if "choices" in response_json and len(response_json["choices"]) > 0:
                generated_text = response_json["choices"][0]["text"]
            else:
                # Fallback if response format is different
                generated_text = response_json.get("text", "")
            
            # Create RequestOutput object compatible with vLLM format
            results.append(RequestOutput(generated_text))
        
        return results

