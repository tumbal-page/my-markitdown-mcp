import os
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

try:
    from markitdown import MarkItDown
except Exception as exc:  # pragma: no cover
    MarkItDown = None
    MARKITDOWN_IMPORT_ERROR = exc
else:
    MARKITDOWN_IMPORT_ERROR = None

app = FastAPI(title="MarkItDown MCP HTTP Wrapper", version="0.1.0")


@app.get("/")
async def root() -> Dict[str, Any]:
    return {
        "service": "MarkItDown MCP Wrapper",
        "status": "ok",
        "docs": "/docs",
        "mcp": "/mcp",
    }


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {"status": "ok"}


@app.post("/mcp")
async def mcp_endpoint(request: Request) -> JSONResponse:
    if MarkItDown is None:
        raise HTTPException(
            status_code=500,
            detail=f"MarkItDown failed to import: {MARKITDOWN_IMPORT_ERROR}",
        )

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Request body must be valid JSON.")

    tool_name = (payload or {}).get("tool")
    if tool_name not in (None, "convert_document"):
        return JSONResponse(
            {"error": f"Unsupported tool '{tool_name}'. Only 'convert_document' is supported."},
            status_code=400,
        )

    source = (payload or {}).get("source")
    file_path = (payload or {}).get("file_path")

    if not source and not file_path:
        raise HTTPException(
            status_code=400,
            detail="You must send either 'source' or 'file_path'.",
        )

    try:
        md = MarkItDown()

        if file_path:
            result = md.convert(file_path).text_content
        elif source.startswith("http://") or source.startswith("https://"):
            import urllib.request

            tmp_path = "/tmp/markitdown_download"
            with urllib.request.urlopen(source) as response, open(tmp_path, "wb") as fh:
                fh.write(response.read())
            result = md.convert(tmp_path).text_content
        else:
            result = md.convert(source).text_content

        return JSONResponse(
            {
                "tool": "convert_document",
                "status": "success",
                "content": result,
                "mime_type": "text/markdown",
            }
        )
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Conversion failed: {exc}")


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
