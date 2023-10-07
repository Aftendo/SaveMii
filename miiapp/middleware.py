"""
General purpose middleware.
"""
from savemii import settings
from miiapp.models import Ban
from django.http import HttpResponse, JsonResponse
from django.core.exceptions import ObjectDoesNotExist


class MiiAppMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        if settings.MAINTENANCE:
            if request.path.startswith("/api/") or request.path.startswith("/mii/"):
                return JsonResponse({"error": True, "message": "Service in maintenance."})
            else:
                return HttpResponse("Service in maintenance.")
        if request.user.is_authenticated:
            try:
                ban = Ban.objects.get(target=request.user)
                return HttpResponse("You've been banned by "+ban.source.username+" for the following reason: "+ban.reason)
            except ObjectDoesNotExist:
                pass
        if request.user_agent.is_mobile or request.user_agent.is_tablet:
            request.is_mobile = True
        else:
            request.is_mobile = False
        request.version = settings.VERSION
        response = self.get_response(request)
        return response