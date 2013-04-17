var channel = document.location.host;
var nickname = "Anonymous";

$(function() {
    if (!window.console) window.console = {};
    if (!window.console.log) window.console.log = function() {};

    nickname = prompt("Enter your nickname: ", nickname);

    $('#post').attr('disabled', 'disabled');
    $("#messageform").on("submit", function() {
        sendMessage();
        return false;
    });
    $("#messageform").on("keypress", function(e) {
        if (e.keyCode == 13) {
            sendMessage();
            return false;
        }
    });
    $("#message").select();
    setTimeout(updater.start, 0);
});

function sendMessage() {
    var message = $("#message").val();
    $("#message").val('').select();
    updater.sendMessage(message);
}

var updater = {
    socket: null,

    send: function(data) {
        updater.socket.send(JSON.stringify(data));
    },

    start: function() {
        updater.socket = new WebSocket('ws://'+document.location.host+'/socket');

        updater.socket.onmessage = function(event) {
            var data = JSON.parse(event.data);
            if (data.type == 'online')
                $('#count').text(data.count)
            else if (data.type == 'last')
                for (var i = 0; i < data.last.length; i++)
                    updater.showMessage(data.last[i])
            else if (data.type == 'message')
                updater.showMessage(data);
        }

        updater.socket.onopen = function(event) {
            $('#post').removeAttr('disabled');
            updater.send({
                'channel': channel,
                'nickname': nickname,
                'type': 'connected',
            });
        }

        updater.socket.onclose = function () {
            if (confirm('Socket disconnected.\nReconnect?'))
                setTimeout(updater.start, 0);
        }
    },

    sendMessage: function(message) {
        message = message.trim();
        if (message) {
            var data = {
                type: 'message',
                body: message
            };
            updater.send(data);
        }
    },

    showMessage: function(message) {
        if ($("#m" + message.id).length > 0) return;
        var node = $(message.html.trim());
        node.hide();
        $("#inbox").append(node);
        node.slideDown();
    }
};
