import asgi_redis

# set message expiry to 2 seconds
channel_layer = asgi_redis.RedisChannelLayer(expiry=2)

AUV_SEND_CHANNEL = 'auv.send'
AUV_UPDATE_CHANNEL = 'auv.update'
NAVIGATION_CHANNEL = 'nav.send'
