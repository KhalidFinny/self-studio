from django.shortcuts import render
from django.http import StreamingHttpResponse, JsonResponse
from .services import CameraService

def index(request):
    return render(request, 'studio/index.html')

def video_feed(request):
    service = CameraService()
    return StreamingHttpResponse(service.generate_frames(),
                               content_type='multipart/x-mixed-replace; boundary=frame')

def status(request):
    service = CameraService()
    return JsonResponse(service.get_status())

def ar(request):
    return render(request, 'studio/ar.html')
