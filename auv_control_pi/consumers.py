

# Connected to websocket.connect
def ws_add(message):
    # Accept the incoming connection
    message.reply_channel.send({"accept": True})
    # Add them to the chat group



# Connected to websocket.receive
def ws_message(message):
    pass

# Connected to websocket.disconnect
def ws_disconnect(message):
    pass
