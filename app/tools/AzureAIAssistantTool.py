# src/tester_crew/tools/azure_ai_assistant.py
import os
import json
import time
import logging
from typing import Optional, Dict, List, Any
from azure.identity import DefaultAzureCredential
from openai import AzureOpenAI
from pydantic import Field, ConfigDict, ValidationError
from crewai.tools import BaseTool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AzureAIAssistantTool(BaseTool):
    name: str = Field(default="Azure AI Assistant")
    description: str = Field(
        default="Interacts with Azure OpenAI Assistants for knowledge retrieval",
    )
    api_version: str = Field(default="2024-05-01-preview")
    assistant_name: Optional[str] = Field(default=None)
    assistant_config: List[Dict] = Field(default_factory=list)
    client: Any = Field(default=None)
    assistant_id: str = Field(default="")
    api_key: Optional[str] = Field(default=None)
    max_wait_time: int = Field(default=300, description="Maximum wait time in seconds for completion")

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._validate_config()
        self.client = self._initialize_client()
        self.assistant_id = self._get_assistant_id(self.assistant_name)
        logger.info(f"Initialized Azure AI Assistant with ID: {self.assistant_id}")

    def _validate_config(self):
        """Validate configuration parameters"""
        if not os.getenv("AZURE_OPENAI_ENDPOINT"):
            raise ValueError("AZURE_OPENAI_ENDPOINT environment variable is required")
        
        try:
            self.assistant_config = json.loads(os.getenv("OPENAI_ASSISTANTS", "[]"))
        except json.JSONDecodeError as e:
            raise ValueError("Invalid JSON in OPENAI_ASSISTANTS environment variable") from e

        if not isinstance(self.assistant_config, list):
            raise ValueError("OPENAI_ASSISTANTS should contain a JSON array of assistants")

    def _get_assistant_id(self, name: Optional[str]) -> str:
        """Get assistant ID from configuration"""
        if not self.assistant_config:
            raise ValueError("No assistants configured in OPENAI_ASSISTANTS")
        
        if name:
            for assistant in self.assistant_config:
                if assistant.get("title") == name:
                    return assistant["id"]
            raise ValueError(f"Assistant '{name}' not found in configuration")
        
        return self.assistant_config[0]["id"]

    def _initialize_client(self):
        """Initialize Azure OpenAI client with multiple authentication options"""
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        
        # Try API key first if provided
        if self.api_key:
            logger.info("Using API key authentication")
            return AzureOpenAI(
                api_key=self.api_key,
                azure_endpoint=endpoint,
                api_version=self.api_version
            )
        
        # Fallback to Azure AD authentication
        try:
            logger.info("Using Azure AD authentication")
            token_provider = DefaultAzureCredential()
            return AzureOpenAI(
                azure_ad_token_provider=lambda: token_provider.get_token(
                    "https://cognitiveservices.azure.com/.default"
                ).token,
                azure_endpoint=endpoint,
                api_version=self.api_version
            )
        except Exception as e:
            raise RuntimeError("Failed to initialize Azure OpenAI client") from e

    def _process_message(self, thread_id: str, run_id: str) -> str:
        """Monitor and process the assistant run with timeout"""
        start_time = time.time()
        
        while time.time() - start_time < self.max_wait_time:
            try:
                run = self.client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run_id
                )
                logger.debug(f"Run status: {run.status}")

                if run.status == 'completed':
                    messages = self.client.beta.threads.messages.list(
                        thread_id=thread_id,
                        order="asc"
                    )
                    return self._extract_response(messages.data)
                
                if run.status in ['failed', 'cancelled', 'expired']:
                    error_msg = run.last_error.message if run.last_error else "Unknown error"
                    raise RuntimeError(f"Assistant run failed: {error_msg}")
                
                if run.status == 'requires_action':
                    raise RuntimeError("Assistant requires action which is not implemented")
                
                time.sleep(5)
            
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
                raise

        raise TimeoutError(f"Assistant did not complete within {self.max_wait_time} seconds")

    def _extract_response(self, messages: List[Any]) -> str:
        """Extract and format the assistant response"""
        for message in reversed(messages):
            if message.role == "assistant" and message.content:
                for content in message.content:
                    if hasattr(content, 'text') and content.text.value:
                        return content.text.value
        return "No response found from assistant"

    def _run(self, query: str) -> str:
        """Execute the main assistant interaction flow"""
        try:
            logger.info(f"Creating new thread for query: {query[:50]}...")
            thread = self.client.beta.threads.create()
            
            logger.debug("Adding user message to thread")
            self.client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=query
            )
            
            logger.info(f"Starting assistant run with ID: {self.assistant_id}")
            run = self.client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=self.assistant_id
            )
            
            logger.debug(f"Started run {run.id}")
            return self._process_message(thread.id, run.id)
        
        except ValidationError as e:
            logger.error(f"Configuration validation error: {str(e)}")
            return f"Configuration error: {str(e)}"
        except Exception as e:
            logger.error(f"Assistant interaction failed: {str(e)}")
            return f"Assistant error: {str(e)}"