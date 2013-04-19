var channel = document.location.host;
var title = 'Chat';
var nickname = "Anonymous";
var blured = false;
var unread_messages = 0;

String.prototype.format = function() {
  var formatted = this;
  for (var i = 0; i < arguments.length; i++) {
    var regexp = new RegExp('\\{'+i+'\\}', 'gi');
    formatted = formatted.replace(regexp, arguments[i]);
  }
  return formatted;
}

$(function() {
    if (!window.console) window.console = {};
    if (!window.console.log) window.console.log = function() {};

    nickname = prompt("Enter your nickname: ", nickname);

    $('#post').attr('disabled', 'disabled');
    $("#messageform").on("submit", function() {
        proccessMessage();
        return false;
    });
    $("#messageform").on("keypress", function(e) {
        if (e.keyCode == 13) {
            proccessMessage();
            return false;
        }
    });
    $("#message").select();
    $(window).blur(function() {
        blured = true;
    });
    $(window).focus(function() {
        blured = false;
        unread_messages = 0;
        document.title = title;
        $("#message").select();
    });
    setTimeout(updater.start, 0);
});

function onMessage() {
    if (blured) {
        unread_messages += 1;
        document.title = '(' + unread_messages + ') ' + title;
    }
}

function proccessCommand(command) {
    var arguments = command.split(' ');
    var command = arguments.shift();
    updater.sendCommand(command, arguments);
}

function proccessMessage() {
    var message = $("#message").val();
    if (message.charAt(0) == '/')
        proccessCommand(message.substr(1, message.lenght))
    else {
        updater.sendMessage(message)
    }
    $("#message").val('').select();
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
            switch (data.type) {
                case 'online':
                    $('#count').text(data.count);
                    updater.showMessage(updater.makeMessage(data.user + ' ' + data.status));
                    break;
                case 'service':
                    updater.showMessage(updater.makeMessage(data.msg));
                    break;
                case 'last':
                    for (var i = 0; i < data.last.length; i++)
                        updater.showMessage(data.last[i])
                    break;
                case 'message':
                    updater.showMessage(data);
                    break;
                default:
                    break;
            }
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
            updater.showMessage(updater.makeMessage('Socket disconnected. Reconnect in 5 seconds.'));
            setTimeout(updater.start, 5000);
        }
    },

    sendMessage: function(message) {
        message = message.trim();
        if (message) {
            var data = {
                type: 'message',
                body: message,
            };
            updater.send(data);
        }
    },

    sendCommand: function(command, arguments) {
        var data = {
            type: 'command',
            command: command,
            arguments: arguments,
        };
        updater.send(data);
    },

    makeMessage: function(string) {
        var template = '<div class="message"><div class="alert-info">* {0}</div></div>';
        var message = {
            html: template.format(string),
        };
        return message;
    },

    showMessage: function(message) {
        if ($("#m" + message.id).length > 0) return;
        var node = $(message.html.trim());
        node.hide();
        $("#inbox").append(node);
        node.slideDown();
        if (message.id) onMessage();
    }
};
