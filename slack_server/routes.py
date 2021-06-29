import insert
import public_key
import slack_action
import slack_command
import slack_oauth
import web

from flask import render_template
from server import server


server.register_blueprint(insert.view, url_prefix="/insert")
server.register_blueprint(public_key.view, url_prefix="/public_key")
server.register_blueprint(slack_action.view, url_prefix="/slack/action")
server.register_blueprint(slack_command.view, url_prefix="/slack/command")
server.register_blueprint(slack_oauth.view, url_prefix="/slack/oauth")
server.register_blueprint(web.root_view, url_prefix="/")
server.register_blueprint(web.privacy_view, url_prefix="/privacy")
server.register_blueprint(web.configure_view, url_prefix="/configure")


@server.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404
