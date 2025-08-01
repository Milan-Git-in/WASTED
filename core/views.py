from django.http import JsonResponse
from .Supabase import supabase  # assuming you renamed it correctly

def check_storage(request):
    try:
        buckets = supabase.storage.list_buckets()
        return JsonResponse({"status": "ok", "buckets": buckets})
    except Exception as e:
        return JsonResponse({"status": "error", "error": str(e)}, status=500)
