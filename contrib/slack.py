from flask import jsonify


def _slack_msg(msg, color):
    return jsonify({
        'attachments': [
            {
                'fallback': msg,
                'text': msg,
                'color': color
            }
        ]
    })


def warning(msg):
    return _slack_msg(msg, 'warning')


def success(msg):
    return _slack_msg(msg, 'good')


def error(msg):
    return _slack_msg(msg, 'danger')


def info(msg):
    return jsonify({
        'attachments': [
            {
                'fallback': msg,
                'text': msg
            }
        ]
    })
