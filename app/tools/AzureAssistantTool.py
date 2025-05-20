from typing import Type, Optional
from crewai.tools import BaseTool
from openai import AzureOpenAI
from pydantic import BaseModel, Field, ConfigDict
import time

class AzureAssistantInputSchema(BaseModel):
    query: str = Field(..., description="User query to process using Azure Assistant")

class AzureAssistantTool(BaseTool):
    name: str = "Ask Azure AI"
    description: str = "Tool that queries Azure OpenAI Assistant with file search capabilities"
    args_schema: Type[BaseModel] = AzureAssistantInputSchema
    
    # Add model_config to allow arbitrary attributes
    model_config = ConfigDict(arbitrary_types_allowed=True, extra='allow')
    
    # Alternatively, you can explicitly define all fields:
    # assistant_id: str = Field(default="asst_286dgsw8Hl1XOFoCXKfeEzt3")
    # vector_store_id: str = Field(default="vs_fgTQGjH9ef9YJrWMi7s2rcUA")
    # client: Optional[AzureOpenAI] = None

    def __init__(self):
        super().__init__()
        self.assistant_id = "asst_286dgsw8Hl1XOFoCXKfeEzt3"  # Replace with your actual ID
        self.vector_store_id = "vs_fgTQGjH9ef9YJrWMi7s2rcUA"  # Replace with your vector store ID
        self.client = self._init_client()
        self._ensure_assistant_exists()

    def _init_client(self):
        return AzureOpenAI(
            azure_endpoint="https://semng-openai-service.openai.azure.com/",
            api_key="69abd24f7af34cf9aa7f0168e992e586",
            api_version="2024-05-01-preview"
        ) 

    def _ensure_assistant_exists(self):
        try:
            # Verify if assistant exists
            self.client.beta.assistants.retrieve(self.assistant_id)
        except:
            # Create new assistant if it doesn't exist
            self.assistant_id = self._create_assistant()

    def _create_assistant(self):
        assistant = self.client.beta.assistants.create(
            model="gpt-4o",
            name="CrewAI Document Assistant",
            instructions="Always cite document names from files",
            tools=[{"type": "file_search"}],
            tool_resources={
                "file_search": {"vector_store_ids": [self.vector_store_id]}
            },
            temperature=0.7
        )
        return assistant.id

    def _run(self, query: str) -> str:
        thread = self.client.beta.threads.create()
        
        self.client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=query
        )

        run = self.client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=self.assistant_id
        )

        while run.status in ['queued', 'in_progress', 'cancelling']:
            time.sleep(1)
            run = self.client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )

        if run.status == 'completed':
            return self._get_response(thread)
        return f"Error: {run.status}"

    def _get_response(self, thread):
        messages = self.client.beta.threads.messages.list(
            thread_id=thread.id,
            order="desc"
        )
        
        for message in messages.data:
            if message.role == "assistant":
                return self._format_message(message)
        return "No response found"

    def _format_message(self, message):
        response = []
        for content in message.content:
            if content.type == "text":
                text = content.text.value
                for annotation in content.text.annotations:
                    try:
                        if annotation.type == "file_citation":
                            citation = f"\n[Source: {annotation.text} (File ID: {annotation.file_citation.file_id})]"
                            text = text.replace(annotation.text, citation)
                    except AttributeError:
                        continue
                response.append(text)
        return "\n".join(response)
