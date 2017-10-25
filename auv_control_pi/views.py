from django.views.generic import TemplateView


class WebsocketView(TemplateView):
    template_name = 'auv_control_pi/index.html'

