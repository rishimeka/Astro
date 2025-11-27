import dotenv
import os
from openai import OpenAI
from langgraph.graph import StateGraph

dotenv.load_dotenv()
client = OpenAI()

def llm_step(state):
    res = client.chat.completions.create(model="gpt-4.1", messages=[{"role": "user", "content": state["input"]}])
    return {"output": res.choices[0].message.content}

graph = StateGraph(dict).add_node("llm", llm_step).set_entry_point("llm").compile()
print(graph.invoke({"input": "Hello"}))