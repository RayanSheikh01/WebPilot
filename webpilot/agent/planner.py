from pathlib import Path
from typing import List, Dict
from .tools import TOOL_SCHEMAS

SYSTEM_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "system.md"


class Planner:
    def __init__(self, agent, tool_executor, budget_tracker):
        self.agent = agent
        self.tool_executor = tool_executor
        self.budget_tracker = budget_tracker

    async def run(self, prompt: str):
        system_prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
        messages = [{"role": "user", "content": prompt}]
        system = [{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}]

        tools = TOOL_SCHEMAS
        while True:
            response = await self.agent.run({
                "system": system,
                "messages": messages,
                "tools": tools,
            })
            if "answer" in response:
                return LoopResult(answer=response["answer"], tool_calls=response.get("tool_calls", []))
            elif "tool_calls" in response:
                for call in response["tool_calls"]:
                    name = call["name"]
                    input = call["input"]
                    output = await self.tool_executor.run(name, input)
                    messages.append({"role": "assistant", "content": {"tool_call": {"name": name, "input": input, "output": output}}})
            else:
                raise ValueError("Agent response must contain either 'answer' or 'tool_calls'")
            



class LoopResult:
    def __init__(self, answer: str, tool_calls: List[Dict]):
        self.answer = answer
        self.tool_calls = tool_calls
        
EXPECTED_NAMES = { 
    "web_search",
    "browser_goto",
    "browser_get_text",
    "browser_get_links",
    "browser_screenshot",
    "browser_back",
    "note",
    "cite",
    "finish",
}


        
