import logging
import json
import os
import base64
import chainlit as cl
from openai import AsyncOpenAI
from dotenv import load_dotenv

from utils.csv_utils import prepare_file_for_api
from utils.image_utils import encode_image
from utils.history_utils import truncate_history
from utils.tavily_utils import tavily_search
from utils.cleanup_utils import cleanup_on_exit, cleanup_session
from utils.tool_executor import execute_tool, handle_code_retry
from utils.chat_start import start
from utils.logger_config import logger


from tools.types import ToolResult, ToolResultType
load_dotenv()

# ----------------- OpenAI Client -----------------
client = AsyncOpenAI(
    api_key=os.getenv("API_KEY"),
    base_url="https://api.ai.it.ufl.edu/v1",
)
cl.instrument_openai()


#function to stream text response
async def stream_text_response(input_payload, tools):
    msg = cl.Message(content="")
    await msg.send()

    async with client.responses.stream(
        model=cl.user_session.get("settings")["model"],
        input=input_payload,
        tools=tools,
        store=True,
    ) as stream:
        async for event in stream:
            if event.type == "response.output_text.delta":
                await msg.stream_token(event.delta)
            elif event.type == "response.error":
                await msg.stream_token(f"\n❌ Error: {event.error}")
            elif event.type == "response.completed":
                await msg.update()
        final_response = await stream.get_final_response()
        return final_response
    
# ----------------- On Message -----------------
@cl.on_message
async def on_message(message: cl.Message):
    history = cl.user_session.get("message_history", [])

    if len(history) > 10:
        history = truncate_history(history)

    # --- File Handling ---
    file_blocks = []
    if message.elements:
        for el in message.elements:
            print("message elements",el)
            print("message type",el.type)

            prepared,error = prepare_file_for_api(el)
            file_blocks.extend(prepared)

    # Build user message 
    user_message = {
        "role": "user",
        "content": [
            {"type": "input_text", "text": message.content},
            *file_blocks
        ]
    }
    history.append(user_message)

    with open("tools.json") as f:
        tools = json.load(f)

    try:
        response = await stream_text_response(history, tools)
        # --- Handle tool calls ---
        if response and response.output:
            if response.output_text:
                history.append({
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": response.output_text}]
                })
            for item in response.output:
                if item.type in ["tool_call", "function_call"]:
                    tool_name = item.name
                    tool_args = json.loads(item.arguments)
                    tool_call_id = item.id

                    # Custom tools (normalisation, clustering, integration, tavily)
                    if tool_name in ["tavily_search","local_code_run"]:
                        tool_results = await execute_tool(tool_name, tool_args)
                        tool_content = []

                        if tool_name == "local_code_run" and any(r.error for r in tool_results):
                            tool_results = await handle_code_retry(client,tools,tool_results,history) # try resolving error in self-contained way

                        for result in tool_results:
                            if result.error:
                                logger.error(f"Tool '{tool_name}' execution error: {result.content}")
                                tool_content.append(f"Error: {result.content}")
                            elif result.type == ToolResultType.text:
                                tool_content.append(result.content)
                                if tool_name != "tavily_search": #tavily search will be handled in the follow-up
                                    await cl.Message(content=f"[{tool_name}] {result.content}").send()
                            elif result.type == ToolResultType.image:
                                img_b64 = encode_image(result.content)
                                desc = result.desc if result.desc else "Image"
                                tool_content.append(f"![{desc}](data:image/png;base64,{img_b64})")
                                await cl.Message(
                                    content=result.desc,
                                    elements=[cl.Image(path=result.content, caption=result.desc)],
                                ).send()
                            

                        tool_message = {
                            "role": "assistant",
                            "content": [ {"type": "output_text" , "text": f"Tool `{tool_name}` result (call_id={tool_call_id}):\n" +
                                         "\n".join(tool_content)}]
                        }

                        history.append(tool_message)
                        
                        follow_up = await stream_text_response(history, tools)

                        history.append({
                            "role": "assistant",
                            "content": [
                                {"type": "output_text", "text": follow_up.output_text}]
                        })

                        #checking token usage
                        logger.info(f"Response usage: in={follow_up.usage.input_tokens}, out={follow_up.usage.output_tokens}")


        # Save history back
        cl.user_session.set("message_history", history)
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        await cl.Message(content=f"❌ Error: {str(e)}").send()


# ----------------- Entrypoint -----------------
if __name__ == "__main__":
    from chainlit.cli import run_chainlit
    run_chainlit(__file__)
