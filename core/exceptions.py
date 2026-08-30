from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    """
    DRF 기본 에러 형태({detail: ...} / 필드별 dict)를 목업과 같은 {error: "..."}로 통일한다.
    프론트는 거의 모든 곳에서 `data.error`를 읽는다.
    """
    response = exception_handler(exc, context)
    if response is None:
        return None

    data = response.data
    if isinstance(data, dict):
        if "detail" in data:
            response.data = {"error": str(data["detail"])}
        elif "error" in data:
            pass
        else:
            # 시리얼라이저 검증 에러: 첫 번째 메시지를 뽑아준다
            first = next(iter(data.values()), "요청이 올바르지 않습니다.")
            if isinstance(first, (list, tuple)):
                first = first[0] if first else "요청이 올바르지 않습니다."
            response.data = {"error": str(first)}
    elif isinstance(data, list):
        response.data = {"error": str(data[0]) if data else "요청이 올바르지 않습니다."}
    return response
