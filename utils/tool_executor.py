import json
import logging
from tools.types import ToolResult, ToolResultType
from tools.local_code_runner import run_code_sandboxed
from utils.tavily_utils import tavily_search
import chainlit as cl
from typing import Any, Dict

logger = logging.getLogger(__name__)
MAX_CODE_RETRIES = 2



# ----------------- Tool Executor -----------------
@cl.step(type="tool")
async def execute_tool(tool_name: str, tool_input: Dict[str, Any]):
    """Run custom backend tools (not built-ins)."""
    try:
        if tool_name == "tavily_search":
            query = tool_input.get("query", "")
            if not query:
                raise ValueError("No query provided for Tavily search.")
            results = await tavily_search(query)
            
            items = results.get("results", [])
            images = results.get("images", [])
            if not items:
                content = "No results found."
            else:
                content = "\n".join(
                    [f"- **{item['title']}**: {item['url']}" for item in items]
                )

            if images:
                    content += "\n\n[Images]\n" + "\n".join(
                        [f"![Image]({img})" for img in images] 
                    )

            return [ToolResult(type=ToolResultType.text, content=content)]
        
        elif tool_name == "local_code_run":
            code = tool_input.get("code", "")
            timeout = int(tool_input.get("timeout_sec", 15))
            if not code.strip():
                return [ToolResult(type=ToolResultType.text, content="No code provided." , error=True)]
            session_id = cl.user_session.get("id")
            try:
                results = await run_code_sandboxed(code, timeout, session_id)
                logger.info(f"Code runner executed with {len(results)} results.")
                return results
            except Exception as e:
                return [ToolResult(type=ToolResultType.text, content=f"Runner error: {e}", error=True)]        

        else:
            raise ValueError(f"Tool '{tool_name}' not recognized.")
    except Exception as e:
        return [ToolResult(type=ToolResultType.text, content = f"Error: {str(e)}", error=True)]
    



#----------------- Retry Code Execution -----------------
async def handle_code_retry(client, tools, tool_results, history):
    """
    Retry code execution up to MAX_CODE_RETRIES times if errors persist.
    Uses the same Responses API + tool_call loop each time.
    """
    for attempt in range(1, MAX_CODE_RETRIES + 1):

        await cl.Message(
            content=f"⚙️ Attempt {attempt}: code execution failed — model will try to fix and re-run..."
        ).send()
        
        logger.info(f"Code execution failed on attempt {attempt}: {tool_results[0].content}")
        # Create repair instruction
        retry_instruction = {
            "role": "assistant",
            "content": [
                {
                    "type": "output_text",
                    "text": (
                        f"The previous code execution failed with the following error:\n\n"
                        f"{tool_results[0].content[:1500]}\n\n"
                        "Please fix the code and re-invoke the `local_code_run` tool "
                        "with corrected code. Do not include explanations, only call the tool again."
                    ),
                }
            ],
        }

        # Request model to produce fixed code
        retry_response = await client.responses.create(
            model=cl.user_session.get("settings")["model"],
            input=history + [retry_instruction],
            # previous_response_id=cl.user_session.get("last_response_id", None),
            tools=tools,
            # truncate="auto",
            store=True,
        )

        # Execute new tool call if present
        new_tool_results = []
        if retry_response.output:
            # cl.user_session.set("last_response_id", retry_response.id)
            for retry_item in retry_response.output:
                if retry_item.type in ["tool_call", "function_call"]:
                    retry_tool_name = retry_item.name
                    retry_tool_args = json.loads(retry_item.arguments)
                    new_tool_results = await execute_tool(retry_tool_name, retry_tool_args)
        elif retry_response.output_text:
            return [ToolResult(type=ToolResultType.text, content=retry_response.output_text, error=True)]

        # if succeeded (no errors), stop looping
        if new_tool_results and not any(r.error for r in new_tool_results):
            await cl.Message(
                content=f"✅ Code fixed and executed successfully on attempt {attempt}."
            ).send()
            return new_tool_results

        # prepare for next retry
        tool_results = new_tool_results or tool_results

    return tool_results #if all retries exhausted