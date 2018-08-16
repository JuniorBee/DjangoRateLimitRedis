from django.conf import settings
from django.utils import timezone
from django.http import HttpResponseForbidden

from datetime import datetime
from datetime import timedelta


def convert_bytes(data):
    if isinstance(data, bytes):
        return data.decode('ascii')
    if isinstance(data, dict):
        return dict(map(convert_bytes, data.items()))
    if isinstance(data, tuple):
        return tuple(map(convert_bytes, data))
    return data


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def rate_limit(rate, **outer_args):
    def decorator(func):
        def wrap(request, *args, **kwargs):
            redis = getattr(settings, 'DJANGO_LIMIT_REDIS')
            ip = get_client_ip(request)
            data = redis.hgetall(ip)
            view_name = func.__name__
            if data:
                data = convert_bytes(data)
                count = int(data.get('count'))
                if datetime.fromtimestamp(timezone.now().timestamp()) - datetime.fromtimestamp(
                        float(data.get('last_request_time'))) < timedelta(**outer_args) and count >= rate and data.get(
                    'name') == view_name:
                    return HttpResponseForbidden('You have made too much requests')
                else:
                    data['count'] = count + 1
                    data['last_request_time'] = timezone.now().timestamp()
                    redis.hmset(ip, data)
            else:
                data = {
                    'count': 1,
                    'last_request_time': timezone.now().timestamp(),
                    'name': view_name
                }
                redis.hmset(ip, data)
                redis.expire(ip, timedelta(**outer_args))
            return func(request, *args, **kwargs)

        return wrap

    return decorator

