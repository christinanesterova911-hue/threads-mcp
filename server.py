import json
import os
import secrets
import urllib.parse
import urllib.request

from mcp.server.mcpserver import MCPServer
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse


mcp = MCPServer("Threads MCP")

APP_ID = os.environ.get("THREADS_APP_ID", "")
APP_SECRET = os.environ.get("THREADS_APP_SECRET", "")
REDIRECT_URI = os.environ.get(
    "THREADS_REDIRECT_URI",
    "https://threads-mcp-98ty.onrender.com/auth/callback",
)

THREADS_API = "https://graph.threads.net/v1.0"

access_token = os.environ.get("THREADS_ACCESS_TOKEN", "")
oauth_state = ""


def api_get(path: str, params: dict | None = None):
    if not access_token:
        raise RuntimeError(
            "Threads is not authorized yet. Open /auth/start first."
        )

    params = params or {}
    url = f"{THREADS_API}/{path.lstrip('/')}"

    if params:
        url += "?" + urllib.parse.urlencode(params)

    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


@mcp.tool()
def test_connection() -> str:
    """Test that the Threads MCP server is running."""
    return "Threads MCP server is working."


@mcp.tool()
def threads_profile() -> dict:
    """Get the connected Threads profile."""
    return api_get(
        "me",
        {
            "fields": (
                "id,username,name,threads_profile_picture_url,"
                "threads_biography"
            )
        },
    )


@mcp.tool()
def threads_posts(limit: int = 10) -> dict:
    """Get recent posts from the connected Threads account."""
    limit = max(1, min(limit, 50))

    return api_get(
        "me/threads",
        {
            "fields": (
                "id,text,timestamp,media_type,"
                "permalink,shortcode"
            ),
            "limit": limit,
        },
    )


@mcp.tool()
def threads_insights() -> dict:
    """Get account-level Threads insights."""
    return api_get(
        "me/threads_insights",
        {
            "metric": (
                "views,likes,replies,reposts,quotes,"
                "followers_count"
            )
        },
    )


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request):
    return JSONResponse(
        {
            "status": "ok",
            "threads_authorized": bool(access_token),
        }
    )


@mcp.custom_route("/auth/start", methods=["GET"])
async def auth_start(request: Request):
    global oauth_state

    if not APP_ID:
        return JSONResponse(
            {"error": "THREADS_APP_ID is not configured"},
            status_code=500,
        )

    oauth_state = secrets.token_urlsafe(32)

    params = {
        "client_id": APP_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": (
            "threads_basic,"
            "threads_content_publish,"
            "threads_manage_insights,"
            "threads_manage_replies"
        ),
        "response_type": "code",
        "state": oauth_state,
    }

    url = (
        "https://threads.net/oauth/authorize?"
        + urllib.parse.urlencode(params)
    )

    return {"oauth_url": url}


@mcp.custom_route("/auth/callback", methods=["GET"])
async def auth_callback(request: Request):
    global access_token

    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")

    if error:
        return JSONResponse(
            {
                "status": "error",
                "error": error,
                "description": request.query_params.get(
                    "error_description"
                ),
            },
            status_code=400,
        )

    if not code:
        return JSONResponse(
            {"error": "Authorization code is missing"},
            status_code=400,
        )

    if not oauth_state or state != oauth_state:
        return JSONResponse(
            {"error": "Invalid OAuth state"},
            status_code=400,
        )

    if not APP_ID or not APP_SECRET:
        return JSONResponse(
            {"error": "Meta app credentials are not configured"},
            status_code=500,
        )

    token_params = urllib.parse.urlencode(
        {
            "client_id": APP_ID,
            "client_secret": APP_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
        }
    )

    token_url = (
        "https://graph.threads.net/oauth/access_token?"
        + token_params
    )

    token_request = urllib.request.Request(
        token_url,
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            token_request,
            timeout=30,
        ) as response:
            token_data = json.loads(
                response.read().decode("utf-8")
            )

        short_token = token_data.get("access_token")

        if not short_token:
            return JSONResponse(
                {
                    "error": "Threads did not return an access token"
                },
                status_code=500,
            )

        long_params = urllib.parse.urlencode(
            {
                "grant_type": "th_exchange_token",
                "client_secret": APP_SECRET,
                "access_token": short_token,
            }
        )

        long_url = (
            "https://graph.threads.net/access_token?"
            + long_params
        )

        with urllib.request.urlopen(
            long_url,
            timeout=30,
        ) as response:
            long_data = json.loads(
                response.read().decode("utf-8")
            )

        access_token = long_data.get(
            "access_token",
            short_token,
        )

        return JSONResponse(
            {
                "status": "success",
                "message": "Threads connected successfully",
            }
        )

    except Exception as exc:
        return JSONResponse(
            {
                "status": "error",
                "message": str(exc),
            },
            status_code=500,
        )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))

    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=port,
        stateless_http=True,
        json_response=True,
    )
