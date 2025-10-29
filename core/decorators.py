"""
커스텀 데코레이터 - 권한 체크
"""
from functools import wraps
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import render


def premium_required(view_func):
    """
    프리미엄 멤버십이 필요한 뷰에 사용하는 데코레이터
    로그인 + 프리미엄 멤버십 확인
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden("로그인이 필요합니다.")
        
        # UserProfile이 없는 경우 자동 생성
        if not hasattr(request.user, 'profile'):
            from .models import UserProfile
            UserProfile.objects.create(user=request.user)
        
        if not request.user.profile.can_upload:
            # JSON 요청인 경우
            if request.headers.get('Content-Type') == 'application/json' or request.META.get('HTTP_ACCEPT') == 'application/json':
                return JsonResponse({
                    'error': '프리미엄 멤버십이 필요한 기능입니다.',
                    'membership_required': True
                }, status=403)
            
            # HTML 요청인 경우
            return render(request, 'core/membership_required.html', status=403)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def owner_or_premium_required(view_func):
    """
    본인 게시물이거나 프리미엄 멤버인 경우에만 수정/삭제 가능
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden("로그인이 필요합니다.")
        
        # audio_id를 kwargs나 URL에서 가져오기
        audio_id = kwargs.get('audio_id')
        
        if audio_id:
            from .models import AudioContent
            try:
                audio = AudioContent.objects.get(id=audio_id)
                
                # 본인 게시물인지 확인
                if audio.user == request.user:
                    return view_func(request, *args, **kwargs)
                
                # 프리미엄 멤버는 본인 게시물만 수정/삭제 가능
                # (다른 사람 게시물은 불가)
                if request.headers.get('Content-Type') == 'application/json':
                    return JsonResponse({
                        'error': '본인의 게시물만 수정/삭제할 수 있습니다.'
                    }, status=403)
                
                return HttpResponseForbidden("본인의 게시물만 수정/삭제할 수 있습니다.")
                
            except AudioContent.DoesNotExist:
                pass
        
        return view_func(request, *args, **kwargs)
    
    return wrapper
