"""Agent loop — STUB.

This file is intentionally incomplete. Your task is to implement the agent.
The interface (class name + run() signature) is fixed so main.py and the
grading harness can invoke it. Everything inside the class is yours to design.

Design decisions you must make (and justify in DESIGN.md):

1. Agent pattern. ReAct? Plan-and-Execute? Multi-agent? Pick one and explain
   why it fits Juice Shop.

2. Loop termination. Max steps? Stop when scoreboard shows N solved? Stop when
   the LLM emits a 'done' signal? Consider cost.

3. Context management. Naive approaches grow messages unboundedly and blow the
   context window within ~40 turns. You need a strategy: summarization, scratchpad,
   selective retention, vector memory — your call.

4. Tool-call error handling. What happens when a tool raises? What does the LLM
   see? How many retries?

5. Progress tracking. How does the agent know what it has already tried? How
   does it know which challenges exist and which it has solved?

You may (and should) add helper modules, state classes, and sub-agents. Anything
under agent/ that is not a protected file is yours to restructure.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .llm import LLMClient, Message
from .tools import REGISTRY


class PentestAgent:
    def __init__(
        self,
        llm: LLMClient,
        target_url: str,
        max_steps: int = 100,
        log_dir: Path | None = None,
    ) -> None:
        self.llm = llm
        self.target_url = target_url
        self.max_steps = max_steps
        self.log_dir = log_dir
        self.registry = REGISTRY

        # Loads the system prompt from file
        system_prompt = Path("agent/prompts/system.md").read_text()

        # The list stores conversation between the agent and LLM
        # LLM uses this to decide what to do next
        self.messages = [
            Message(
                role="system",
                content=system_prompt
            ),
            Message(
                role="user",
                content=f"Start testing the target at {self.target_url}",
                # Starts the task by telling agent what to do
            ),
        ]

        # Tracks how many steps agent has taken
        self.steps_taken = 0
        # Tracks how many tool calls have been made
        self.tool_calls = 0
        # The scratchpad can store notes
        self.scratchpad = []
        # This stores any discovered vulnerabliites
        self.findings = []
        # This keeps track of paths already tested
        self.tested_paths = set()

    def run(self) -> dict[str, Any]:
        """This is the Main ReAct-style agent loop.
        
        The agent will repeatedly:
        1. Send the current conversation to the LLM
        2. Lets the LLM choose the tool
        3. Runs the tool
        4. Sends the tool result back to the LLM
        """

        for step in range(self.max_steps):
            # This tracks how many action steps the agent has taken
            self.steps_taken += 1

            # Asks the LLM what to do next, while giving access to tools
            response = self.llm.complete(
                messages=self.messages,
                tools=self.registry.openai_schemas(),
            ) 

            # Saves the assistant response in memory
            self.messages.append(response)

            # If LLM doesn't request the tool, treat that as final answer
            if not response.tool_calls:
                return {
                    "steps_taken": self.steps_taken,
                    "tool_calls": self.tool_calls,
                    "final_message": response.content or "Agent finished without the final message.",
                }
            
            # This runs each tool requested by LLM
            for tc in response.tool_calls:
                tool = self.registry.get(tc.name)

                # This handles missing tools without crashing the agent
                if tool is None:
                    result = {"error": f"Tool '{tc.name}' was not found."}
                else:
                    try:
                        # Excecutes the tool with the arguments chosen by LLM
                        result = tool.invoke(tc.arguments)
                    except Exception as e:
                        # Returns tool errors back to LLM so it can recover
                        result = {"error": f"{type(e).__name__}: {e}"}
                
                # Saves the strcutrued findings returned by the tools
                if isinstance(result, dict) and "findings" in result:
                    self.findings.extend(result["findings"])
                
                self.tool_calls += 1

                # Sends the tool result back into the conversation
                self.messages.append(
                    Message(
                        role="tool",
                        content=str(result),
                        tool_call_id=tc.id,
                        name=tc.name,
                    )
                )
        # If the loop reaches max_steps, stops to control the cost and runtime
        return {
            "steps_taken": self.steps_taken,
            "tool_calls": self.tool_calls,
            "final_message": "Agent stopped because it reached the maximum step limit.",
        }
        

    def generate_report(self, output_path: Path) -> None:
        """Generate the final pentest report at output_path.

        This is called by main.py after run() completes. The rubric expects the
        report to be grouped by vulnerability class, include evidence captured
        during the run, and include specific remediation advice.

        This report uses the agent's final run information
        """

        # This make sures the output folder exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Opens the file to write the report
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# The Final Pentest Report\n\n")

            # This is a high-level summary of the agent's run
            f.write("## Summary\n")
            f.write("This report was created after running the AI pentesting agent against the OWASP Juice Shop.\n\n")

            # These are the basic statistics about the run
            f.write("## Run Statistics\n")
            f.write(f"- Steps taken: {self.steps_taken}\n")
            f.write(f"- Tool calls made: {self.tool_calls}\n\n")

            # This lists any findings
            f.write("## Our Findings\n")
            if self.findings:
                for finding in self.findings:
                    f.write(f"- Type: {finding.get('type')}\n")
                    f.write(f"  Endpoint: {finding.get('endpoint')}\n")
                    f.write(f"  Payload: {finding.get('payload')}\n")
                    f.write(f"  Severity: {finding.get('severity')}\n\n")
            else:
                f.write("- No structured findings were recorded yet.\n")
            
            # This is the final message from the agent
            f.write("\n## Final Agent Message\n")
            final_message = self.messages[-1].content if self.messages else "No final message available."
            f.write(final_message or "There is no final message available.")

            # This is the generic remediation device
            f.write("\n\n## Remediation\n")
            f.write(
                "The review discovered vulnerabilities, validate affected endpoints, "
                "and apply secure coding practices like input validation, "
                "output encoding, authentication checks, and proper access controls.\n"
            )
            





