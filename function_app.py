import azure.functions as func
import logging
import os
import json
from datetime import datetime, timezone
from openai import AzureOpenAI

from recon_excel import build_workbook
from recon_service import build_rows

# ---- LangGraph agent ----
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_openai import AzureChatOpenAI

 
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)
 
# Set up the Azure OpenAI client once, at module load time
client = AzureOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version="2024-08-01-preview"
)
 
deployment_name = os.environ["AZURE_OPENAI_DEPLOYMENT"]
 
 
@app.route(route="hello_world")
def hello_world(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    name = req.params.get('name')
    if name:
        return func.HttpResponse(f"Hello, {name}.")
    return func.HttpResponse("Hello from Azure Functions!")
 
 
@app.route(route="ask_ai")
def ask_ai(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('AI request received.')
 
    try:
        req_body = req.get_json()
        question = req_body.get('question')
    except ValueError:
        return func.HttpResponse(
            "Please send a JSON body with a 'question' field.",
            status_code=400
        )
 
    if not question:
        return func.HttpResponse(
            "Please include a 'question' field in your request.",
            status_code=400
        )
 
    try:
        response = client.chat.completions.create(
            model=deployment_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": question}
            ],
            max_tokens=500
        )
 
        answer = response.choices[0].message.content
 
        return func.HttpResponse(
            json.dumps({"answer": answer}),
            mimetype="application/json",
            status_code=200
        )
 
    except Exception as e:
        logging.error(f"Error calling Azure OpenAI: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )

 
# Define the shape of state passed through the graph
class AgentState(TypedDict):
    question: str
    answer: str
 
 
# Create the LangChain wrapper around Azure OpenAI
llm = AzureChatOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version="2024-08-01-preview",
    azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
    temperature=0
)
 
 
def think_node(state: AgentState) -> AgentState:
    """A single graph node that calls the LLM and returns an answer."""
    response = llm.invoke([
        {"role": "system", "content": "You are a helpful assistant for data migration tasks."},
        {"role": "user", "content": state["question"]}
    ])
    state["answer"] = response.content
    return state
 
 
# Build the graph
workflow = StateGraph(AgentState)
workflow.add_node("think", think_node)
workflow.set_entry_point("think")
workflow.add_edge("think", END)
graph = workflow.compile()
 
 
@app.route(route="agent_ask")
def agent_ask(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Agent request received.')
 
    try:
        req_body = req.get_json()
        question = req_body.get('question')
    except ValueError:
        return func.HttpResponse(
            "Please send a JSON body with a 'question' field.",
            status_code=400
        )
 
    if not question:
        return func.HttpResponse(
            "Please include a 'question' field in your request.",
            status_code=400
        )
 
    try:
        initial_state = {"question": question, "answer": ""}
        final_state = graph.invoke(initial_state)
 
        return func.HttpResponse(
            json.dumps({"answer": final_state["answer"]}),
            mimetype="application/json",
            status_code=200
        )
 
    except Exception as e:
        logging.error(f"Error running agent: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )



# ---- MT count reconciliation report (called from Business Central codeunit "MT Reconciliation Report") ----
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@app.route(route="reconciliation", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def reconciliation(req: func.HttpRequest) -> func.HttpResponse:
    try:
        payload = req.get_json()
    except ValueError:
        return func.HttpResponse("Request body must be JSON", status_code=400)
    if not isinstance(payload, dict) or not payload.get("tables"):
        return func.HttpResponse("No tables in request", status_code=400)

    try:
        rows = build_rows(payload)
        content = build_workbook(rows)
    except Exception as ex:  # noqa: BLE001
        logging.exception("Reconciliation failed")
        return func.HttpResponse(f"Reconciliation failed: {ex}", status_code=500)

    filename = f"MT_Count_Reconciliation_{datetime.now(timezone.utc):%Y%m%d_%H%M}.xlsx"
    return func.HttpResponse(
        content,
        mimetype=XLSX,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
