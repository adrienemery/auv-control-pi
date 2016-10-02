import asgi_redis
from channels import Group

# set message expiry to 2 seconds
channel_layer = asgi_redis.RedisChannelLayer(expiry=2)

AUV_SEND_CHANNEL = 'auv.send'
NAVIGATION_CHANNEL = 'nav.send'
auv_update_group = Group('auv.update', channel_layer=channel_layer)

