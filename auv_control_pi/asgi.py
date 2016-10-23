import asgi_redis
import asgi_ipc

# set message expiry to 2 seconds
channel_layer = asgi_redis.RedisChannelLayer(expiry=2)
# channel_layer = asgi_ipc.IPCChannelLayer(expiry=2)

AUV_SEND_CHANNEL = 'auv.send'
NAVIGATION_CHANNEL = 'nav.send'
AUV_UPDATE_CHANNEL = 'auv.update'
