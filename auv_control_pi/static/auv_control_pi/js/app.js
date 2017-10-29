var ws = new WebSocket("ws://127.0.0.1:8000/ws");


var vm = new Vue({
    el: '#app',
    data: {
        data: {},
        status: 'disconnected',
        leftMotorSpeed: 0,
        rightMotorSpeed: 0,
        forwardSpeed: 0,
        test: 10,
        initialized: false,
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
            if (this.initialized && this.leftMotorSpeed != this.data.left_motor_speed) {
                this.setLeftMotorSpeed(newSpeed);
            }
        },
        rightMotorSpeed: function (newSpeed) {
            if (this.initialized && this.rightMotorSpeed != this.data.right_motor_speed) {
                this.setRightMotorSpeed(newSpeed);
            }
        },
    }

});

ws.onopen = function () {
    // Web Socket is connected
    vm.status = 'connected';
};

ws.onmessage = function (evt) {
    // message recieved
    vm.data = JSON.parse(evt.data);
    if (!vm.initialized) {
        vm.leftMotorSpeed = vm.data.left_motor_speed;
        vm.rightMotorSpeed = vm.data.right_motor_speed;
        vm.initialized = true;
    }
};

ws.onclose = function () {
    // websocket is closed.
    vm.status = 'disconnected';
};
