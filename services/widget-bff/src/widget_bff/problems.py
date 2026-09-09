from __future__ import annotations

from fastapi.responses import JSONResponse

from widget_bff.models import ProblemDetails


def problem_response(
    *,
    status: int,
    code: str,
    title: str,
    request_id: str,
    detail: str | None = None,
    retry_after: int | None = None,
) -> JSONResponse:
    problem = ProblemDetails(
        type=f"https://widget.amulai.in/problems/{code.replace('_', '-')}",
        title=title,
        status=status,
        code=code,
        request_id=request_id,
        detail=detail,
        retry_after=retry_after,
    )
    headers = {"Cache-Control": "no-store"}
    if retry_after is not None:
        headers["Retry-After"] = str(retry_after)
    return JSONResponse(
        problem.model_dump(exclude_none=True),
        status_code=status,
        media_type="application/problem+json",
        headers=headers,
    )
