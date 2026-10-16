# Design Document

## 1. LLM Choice

**Model:** OpenAI GPT-4o through LiteLLm

**Why this model:** 
I used GPT-4o because it worked with the tool-calling setup in the project.  While I was testing, GPT-4o was able to understand the tool outputs and effectively what was going on. Another reason I chose the model is because this model offers a good balance between performance and cost. This is important because the agent runs multiple steps and tool calls.

## 2. Agent Architecture

**Pattern chosen:** ReAct

**Diagram:**
User Input
|
v
LLM (Reasoning)
|
v
Selects the Tool
|
v
Executes the Tool (SQLi / XSS / API Fuzzer)
|
v
Tool Result
|
v
LLM (Next Reasoning Step)
|
v
Repeats until done or max steps reached

**Why this architecture:** 
I chose the ReAct pattern because it lets the agent switch between the reasoning and tools.  For example, in the login admin challenge, the agent explored the /rest/user/login endpoint, used SQL injection, and analyzed the response.

The Juice Shop web application has different of challenges, so the ReAct works well because the agent is able to adapt based on the results instead of following a fixed plan of action.

### Rejected alternatives

I thought about a multi-agent approach, but I think it would've added unnecessary complexity.  Managing the communication between the multiple agents would increase the overhead without significantly improving the performance.

## 3. Prompting Strategy

**System prompt structure:** 
The system prompt defines the agent as a penetration tester whose goal is to discover any vulnerabilities in the Juice Shop application.  It includes clear instructions about using the tools, avoiding any unnecessary actions, and focusing on finding the issues in the application. It describes what success is and talks about the tool we have available and when to use them.

**Task decomposition:** 
The agent doesn't plan everything in advance. It reasons about the current situation and selects a tool. Then, it observes the result, and decides the next step it should take.

**What did you try and discard?** 
I first used a general system prompt that didn't clearly tell when to use the tools.  This caused the agent to overexplain or repeated steps without making any progress. When I gave a prompt that was too detailed, the agent gave longer responses that didn't really help with finding any vulnerabilities. 

I fixed this by clearly stated the goal, when to use the tools, and keeping response on topic.This helped the agent to take more useful steps.

## 4. Tool Design

| Tool | Purpose | Why you built it |

| SQL Injection Tester | Tests SQL payloads | Useful for login/authentication challenges
| XSS Tester | Tests the reflected XSS | Dectects any input-based vulnerabilities
| API fuzzer | Fuzzes API endpoints | Finds unusual API behavior

SQL Injection Tester
This tool takes an endpoint, parameter, and a HTTP method.  I exposed these parameters so the agent could have flexibility to test the different endpoints and different input fields. The tool handles the payload in code by sending the common SQL injection payloads and then checking for any suspicious responsed.  The LLM is responsible for deciding which endpoint and parameter should be tested.  It's also interpreting the results.

XSS Tester
This tool does the same thing with the endpoints, parameters, and HTTP method.  This makes things easy for the agent.  The tool sends common XSS payloads and checks whether the payload appears in the response.  It helps us detect possible reflected XSS, while the LLM decides whether the result is good and what to do next.

API Fuzzer
Now, the API fuzzer takes an endpoint and an HTTP method.  It keeps the parameters simple.  This makes the LLM generate every fuzzing input manually.  It sends different payloads like unusual IDs, admin-related fields, and SQL-like input.  The code helps by identifying unusual status codes, while the LLM interprets whether those responses suggest weak validation or any other issues.

## 5. Context / Memory Management

This agent uses a simple message history system where the system, user, assistant, and tool messages are stored throughout the execution.  This project used a limited number of steps, so this approach helped to avoid context window problems.

The agent doesn't summarize older messages.  The max_steps parameter is used to limit how large the conversation can grow

It tracks progress by using:
- steps_taken
- tool_calls
- the findings gathered from tool results

This helps the agent remember which endpoints and vulnerabilites have already been tested.

In order to prevent looping, the agent stops when:
- the maximum number of steps is reached
- the LLM no longer needs to request tool calls and returns the final response

## 6. Attack Strategy

The agent follows an opportunistic attack strategy.  It doesn't target specific challenges directly. Instead, it reacts to the results returned from the tools and chooses the next action based on any suspicious behavior.

It explores the endpoints dynamically through tool usage and follows up on:
- status code 200 after  injection attempts
- server errors (500)
- unauthorized responses (401/403)
- reflected input or unusual API behavior.

The exploration strategy favors breadth first and focuses more on the endpoints that appear vulnerable.  A limitation would be that the agent might spend too much time repeatedly testing the same endpoint instead of exploring all available functionality.

## 7. Observed Failures

List at least three specific failures you observed during development and what you changed in response. (Without this, it is very hard to believe you actually ran your agent.)

1. **Failure:** Agent initially produced reports saying that the target  application wasn't accessible and returned errors.
   **Diagnosis:** The Juice Shop wasn't running at the time, so it couldn't connect to the URl
   **Fix:** I restarted and verified the Docker container and confirmed the target was accessible before running the agent again

2. **Failure:** Agent sometimes produced long explanations instead of taking useful actions.
   **Diagnosis:** The original system prompt was too general and didn't emphasize when the tools should be used.
   **Fix:** I updated the system prompt to focus more on the tool usage, vulnerabilities, and keeping the responses clear.

3. **Failure:** I created a directory brute-force tool, but it wasn't contributing any meaningful findings during the agent's run.
   **Diagnosis:** The agent wasn't selecting the tool often, and the resuls were not as useful as the other tools.
   **Fix:** I replaced the this tool with an API fuzzing too; that tested endpoints using different payloads and detecting unusual API behavior.

## 8. Limitations
I believe the agent has several limitations because the of the simple design and tools I chose.

One limitation I think is the SQL injection. It relies on basic payloads and response analysis.  The agent wasn't able to reliably identify blind SQL injection vulnerabilities or more advanced techniques.

The agent is also limited in how it manages context.  All the messages are stored directly in memory without any summarization, longer runs could lead repeated actions.

## 9. Citations

I used ChatGPT for debugging my agent and documentation wording.  Also used to review my pieces of tool implementation.

- HackTricks: https://hacktricks.wiki/en/index.html
Looked at this to see some examples of penetration testing.
