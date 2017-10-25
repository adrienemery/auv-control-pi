var ws = new WebSocket("ws://127.0.0.1:8000/ws");


var vm = new Vue({
    el: '#app',
    data: {
        data: {},
        status: 'disconnected',
        leftMotorSpeed: 0,
        rightMotorSpeed: 0,
    },
    created: function () {
        // created hook
    },
    methods: {
        setLeftMotorSpeed: function (newSpeed) {
            ws.send(JSON.stringify({cmd: 'set_motor_speed', params: {motor_side: 'left', speed: newSpeed}}));
        },
        setRightMotorSpeed: function (newSpeed) {
            ws.send(JSON.stringify({cmd: 'set_motor_speed', params: {motor_side: 'right', speed: newSpeed}}));
        },

    },
    watch: {
        leftMotorSpeed: function (newSpeed) {
            this.setLeftMotorSpeed(newSpeed);
        },
        rightMotorSpeed: function (newSpeed) {
            this.setRightMotorSpeed(newSpeed);
        },

    }

});

ws.onopen = function () {
    // Web Socket is connected
    vm.status = 'connected';
};

ws.onmessage = function (evt) {
    // message recieved
    vm.data = evt.data;
};

ws.onclose = function () {
    // websocket is closed.
    vm.status = 'disconnected';
};
