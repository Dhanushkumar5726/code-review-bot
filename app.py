import os
import json
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

# Load environment variables
load_dotenv(override=True)

from src.graph import build_review_graph

app = FastAPI(
    title="Iterative Code Review Bot API",
    description="FastAPI Backend for Code Review Bot",
    version="1.0"
)

# Allow CORS for local frontend development (e.g. Vite default port 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For production, restrict to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ReviewRequest(BaseModel):
    code: str
    max_iterations: int = 1


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/review")
async def review_code(request: Request, body: ReviewRequest):
    """
    Starts the review process and streams the results back via Server-Sent Events (SSE).
    """

    # Basic API Key validations similar to app.py
    provider = os.getenv("LLM_PROVIDER", "groq").lower()
    if provider == "gemini" and not os.getenv("GOOGLE_API_KEY"):
        return {"error": "GOOGLE_API_KEY not found in .env"}
    elif provider == "groq" and not os.getenv("GROQ_API_KEY"):
        return {"error": "GROQ_API_KEY not found in .env"}
    elif provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        return {"error": "OPENAI_API_KEY not found in .env"}

    graph = build_review_graph()

    initial_state = {
        "original_code": body.code,
        "current_code": body.code,
        "static_analysis_results": "",
        "analysis": "",
        "issues": [],
        "suggestions": [],
        "checklist_results": [],
        "all_checks_passed": False,
        "iteration": 0,
        "max_iterations": body.max_iterations,
        "is_complete": False,
        "review_history": [],
        "final_report": "",
    }

    async def event_generator():
        final_state = initial_state.copy()

        try:
            # We must use graph.stream(). It's a synchronous generator but we can run it in async function.
            # In production with heavier workload you might want to run this in a threadpool (run_in_executor)
            # but for this simple setup it should stream fine.
            for event in graph.stream(initial_state):
                # If client disconnected, break
                if await request.is_disconnected():
                    break
                    
                for node_name, node_output in event.items():
                    status_message = ""
                    if node_name == "static_analyzer":
                        status_message = "⚡ Running fast syntax and static checks..."
                    elif node_name == "analyzer":
                        status_message = "🔍 Running deep AI analysis..."
                    elif node_name == "issue_finder":
                        issues = node_output.get("issues", [])
                        status_message = f"🐛 Found {len(issues)} issue(s)..."
                    elif node_name == "fix_suggester":
                        status_message = "🔧 Generating fix suggestions..."
                    elif node_name == "code_fixer":
                        status_message = "✏️ Applying fixes to the code..."
                    elif node_name == "checklist":
                        iteration = node_output.get('iteration', '?')
                        status_message = f"✅ Running quality checklist (Iteration {iteration})..."
                    elif node_name == "report_generator":
                        status_message = "📄 Writing final report draft..."
                    elif node_name == "report_validator":
                        status_message = "🔎 Validating and correcting report..."

                    if status_message:
                        yield {
                            "event": "message",
                            "data": json.dumps({"type": "status", "message": status_message})
                        }
                    
                    if isinstance(node_output, dict):
                        final_state.update(node_output)

            report = final_state.get("final_report", "⚠️ Sorry, an error occurred while generating the report.")
            yield {
                "event": "message",
                "data": json.dumps({"type": "report", "content": report})
            }
            
        except Exception as e:
            yield {
                "event": "message",
                "data": json.dumps({
                    "type": "error", 
                    "message": f"🚨 **Pipeline Interrupted:** {str(e)}\n\nThe LLM Provider may be experiencing severe rate limiting or a 500 error."
                })
            }

    return EventSourceResponse(event_generator())
