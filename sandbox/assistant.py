import os
import time
from openai import AzureOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AzureAIAssistant:
    def __init__(self):
        self._init_client()
        self.assistant_id = "asst_286dgsw8Hl1XOFoCXKfeEzt3"  # Replace with your ID
        self.vector_store_id = "vs_fgTQGjH9ef9YJrWMi7s2rcUA"
        
        if not self.assistant_id:
            self._create_assistant()

    def _init_client(self):
        self.client = AzureOpenAI(
            azure_endpoint="https://semng-openai-service.openai.azure.com/",
            api_key="69abd24f7af34cf9aa7f0168e992e586",
            api_version="2024-05-01-preview"
        )

    def _create_assistant(self):
        self.assistant = self.client.beta.assistants.create(
            model="gpt-4o",
            name="Document Assistant",
            instructions="Always cite document names from files",
            tools=[{"type": "file_search"}],
            tool_resources={
                "file_search": {"vector_store_ids": [self.vector_store_id]},
                "code_interpreter": {"file_ids": ["assistant-BtZDre2YBWO7n3SnypAkA7j6"]}
            },
            temperature=0.7,
            top_p=1
        )
        self.assistant_id = self.assistant.id

    def process_query(self, query: str):
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
        else:
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
                # Process annotations safely
                for annotation in content.text.annotations:
                    try:
                        if annotation.type == "file_citation":
                            # New annotation structure
                            citation = f"\n[Source: {annotation.text} (File ID: {annotation.file_citation.file_id})]"
                            text = text.replace(annotation.text, citation)
                    except AttributeError as e:
                        print(f"Skipping invalid annotation: {e}")
                response.append(text)
        return "\n".join(response)

if __name__ == "__main__":
    assistant = AzureAIAssistant()
    
    print("Assistant ready. Type 'exit' to quit.")
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() == 'exit':
            break
            
        response = assistant.process_query(user_input)
        print(f"\nAssistant: {response}")

    print("Session ended.")