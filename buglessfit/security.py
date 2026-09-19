CONTENT_SECURITY_POLICY = "; ".join(
    (
        "default-src 'self'",
        "base-uri 'self'",
        "object-src 'none'",
        "frame-ancestors 'none'",
        "form-action 'self'",
        "script-src 'self' https://cdn.jsdelivr.net",
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com "
        "https://fonts.googleapis.com https://use.fontawesome.com "
        "https://cdnjs.cloudflare.com",
        "font-src 'self' data: https://fonts.gstatic.com https://use.fontawesome.com "
        "https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://unpkg.com",
        "img-src 'self' data: https:",
        "connect-src 'self'",
        "frame-src https://www.google.com",
        "media-src 'self' https:",
        "worker-src 'none'",
        "manifest-src 'self'",
    )
)


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        response.setdefault(
            "Permissions-Policy",
            "camera=(), geolocation=(), microphone=()",
        )
        response.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        response.setdefault("X-Permitted-Cross-Domain-Policies", "none")
        return response
