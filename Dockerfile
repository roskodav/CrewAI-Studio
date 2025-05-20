FROM python:3.12.10-slim-bookworm

# Install Docker CLI and dependencies
RUN apt-get update && \
    apt-get install -y \
    build-essential \
    curl \
    gnupg \
    lsb-release && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian \
    $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && \
    apt-get install -y docker-ce-cli

# Setup CrewAI Studio
RUN mkdir /CrewAI-Studio
COPY ./requirements.txt /CrewAI-Studio/requirements.txt
WORKDIR /CrewAI-Studio

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

COPY ./ /CrewAI-Studio/

# Fix permissions for Docker socket
RUN groupadd -g 999 docker && \
    usermod -aG docker root

CMD ["streamlit", "run", "./app/app.py", "--server.headless", "true"]
EXPOSE 8501