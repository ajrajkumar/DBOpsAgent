from strands import Agent, tool
import boto3
import os

# 1. Define the AI model

# TODO1: Define the model here

# 2. Create a tool to list Aurora clusters

# TODO2: Add database tool here

# 3. Create the system prompt

# TODO3: Add the system prompt here

# 4. Create the agent
agent = Agent(
    system_prompt=prompt,
    model=model,
    tools=[list_aurora_clusters]
)

while True:
    question = input("\n💬 Your question: ")
    if question.lower() in ['exit', 'quit']:
        break
    response = agent(question)
    #print(f"📊 {response}")