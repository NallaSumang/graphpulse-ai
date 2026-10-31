import os
from pathlib import Path
from typing import Optional
from google import genai
from google.genai import types

class GemmaAuditor:
    def __init__(self, runtime: str, api_key: Optional[str] = None):
        self.runtime = runtime
        self.api_key = api_key
        
        if self.runtime == "gemini" and not self.api_key:
            raise ValueError("GEMINI_API_KEY is required for the Gemini API runtime. Please enter it in the sidebar.")

    def audit(
        self,
        question: str,
        graph_json_path: Path,
        report_path: Path,
        screenshot: Optional[bytes] = None,
        screenshot_name: Optional[str] = None,
    ) -> str:
        # ARCHITECTURAL FIX: Context Compression
        # We strictly cap the report to 8,000 characters (~2,000 tokens) 
        # and drop the raw graph.json entirely to prevent 429 RESOURCE_EXHAUSTED errors.
        report_text = report_path.read_text(encoding="utf-8")[:8000] if report_path.exists() else "Graph report missing."
        
        prompt = (
            "You are a Principal Systems Architect. Using the following deterministic Graphify AST report, "
            "answer the developer's PR blast-radius question. Cite specific God Nodes, communities, and EXTRACTED edges.\n\n"
            f"--- GRAPH REPORT ---\n{report_text}\n\n"
            f"--- QUESTION ---\n{question}"
        )

        # Execute Gemini API Call
        if self.runtime == "gemini":
            return self._audit_gemini(prompt, screenshot, screenshot_name)
            
        # Fallback stub for local models (if installed later)
        return "Local Ollama runtime is currently unavailable. Please switch to Gemini API."

    def _audit_gemini(self, prompt: str, screenshot: Optional[bytes], screenshot_name: Optional[str]) -> str:
        client = genai.Client(api_key=self.api_key)
        contents = [prompt]
        
        # Handle multimodal vision upload if a screenshot is provided
        if screenshot and screenshot_name:
            temp_img = Path(screenshot_name)
            temp_img.write_bytes(screenshot)
            try:
                uploaded_file = client.files.upload(file=str(temp_img))
                contents.insert(0, uploaded_file)
            except Exception as upload_exc:
                raise RuntimeError(f"Failed to upload graph screenshot: {str(upload_exc)}")

        try:
            response = client.models.generate_content(
                model="gemma-4-26b-a4b-it",
                contents=contents,
            )
            return response.text or "No response generated."
        except Exception as e:
            raise RuntimeError(f"Gemma 4 API Error: {str(e)}")