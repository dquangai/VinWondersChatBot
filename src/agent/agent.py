import os
import re
import json
from typing import List, Dict, Any, Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.tools.vinwonders_tools import execute_vinwonders_tool

class ReActAgent:
    """
    A ReAct-style Agent that follows the Thought-Action-Observation loop.
    """
    
    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 10):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.history = []

    def get_system_prompt(self) -> str:
        """
        System prompt that instructs the agent to follow ReAct.
        """
        tool_descriptions = "\n".join([
            f"- {t['name']}: {t['description']}\n  Parameters: {t['parameters']}"
            for t in self.tools
        ])
        return f"""You are an intelligent travel assistant for VinWonders. You have access to the following tools:
{tool_descriptions}

Use the following format for your responses:
Thought: your line of reasoning.
Action: tool_name({{"param1": "value1", "param2": ["list1", "list2"]}})
Observation: result of the tool call.
... (repeat Thought/Action/Observation until you have enough information)
Final Answer: your final response to the user.

IMPORTANT: 
- Your Action must be exactly formatted as: Action: tool_name({{...JSON arguments...}})
- Wait for the Observation before continuing. If you output an Action, stop generating and DO NOT hallucinate the Observation. The system will provide the Observation.
- All JSON arguments in Action must be strictly valid JSON. 
"""

    def run(self, user_input: str) -> str:
        """
        ReAct loop logic.
        """
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})
        
        current_prompt = user_input
        steps = 0
        system_prompt = self.get_system_prompt()
        
        # Regex to parse the tool call. Example: Action: tool_name({"arg1": "val"})
        action_regex = re.compile(r"Action:\s*(\w+)\s*\((.*?)\)", re.DOTALL)
        final_answer_regex = re.compile(r"Final Answer:\s*(.*)", re.DOTALL)

        while steps < self.max_steps:
            try:
                # Generate LLM response
                response_dict = self.llm.generate(current_prompt, system_prompt=system_prompt)
                result = response_dict.get("content", "")
                print(f"\n[Step {steps + 1}] LLM Output:\n{result}\n")
            except Exception as e:
                import time
                if "429" in str(e) or "ResourceExhausted" in str(e):
                    print(f"\n⚠️ Đạt giới hạn API (Quota Exceeded). Đang chờ 15 giây trước khi thử lại...")
                    time.sleep(15)
                    continue
                else:
                    raise e
            
            # Check for Final Answer
            final_match = final_answer_regex.search(result)
            if final_match:
                final_answer = final_match.group(1).strip()
                logger.log_event("AGENT_END", {"steps": steps + 1, "status": "success"})
                return final_answer
            
            # Parse Thought/Action from result
            action_match = action_regex.search(result)
            if action_match:
                tool_name = action_match.group(1)
                args_str = action_match.group(2).strip()
                
                try:
                    args_dict = json.loads(args_str)
                except json.JSONDecodeError:
                    print("Failed to parse arguments as JSON. Trying to clean it up...")
                    try:
                         # Attempt rudimentary cleanup if it has quotes issues (just for safety)
                         args_dict = json.loads(args_str.replace("'", '"'))
                    except:
                         args_dict = {}

                # Execute tool
                observation = self._execute_tool(tool_name, args_dict)
                print(f"Observation: {observation}\n")
                
                # Append to prompt
                current_prompt += f"\n{result}\nObservation: {observation}\n"
            else:
                # Nếu LLM quên dùng format "Final Answer:" mà chỉ chat bình thường, ta sẽ lấy luôn câu chat đó
                logger.log_event("AGENT_END", {"steps": steps, "status": "conversational_fallback"})
                return result.strip()
            
            steps += 1
            
        logger.log_event("AGENT_END", {"steps": steps, "status": "max_steps_reached"})
        return "Agent reached maximum steps without a final answer."

    def _execute_tool(self, tool_name: str, args_dict: dict) -> str:
        """
        Execute tools by name.
        """
        logger.log_event("TOOL_CALL", {"tool": tool_name, "args": args_dict})
        try:
            return execute_vinwonders_tool(tool_name, args_dict)
        except Exception as e:
            return f"Error executing tool {tool_name}: {str(e)}"
