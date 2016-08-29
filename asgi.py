import asgi_redis

# set message expiry to 2 seconds
channel_layer = asgi_redis.RedisChannelLayer(expiry=2)

MOTHERSHIP_SEND_CHANNEL = 'mothership.send'
MOTHERSHIP_UPDATE_CHANNEL = 'mothership.update'
NAVIGATION_CHANNEL = 'nav.send'
