from flask import Blueprint, render_template

from environ import WEBPAGE

configure_view = Blueprint("configure", __name__)
landing_view = Blueprint("page_not_found", __name__)
privacy_view = Blueprint("privacy", __name__)


@landing_view.route("", methods=["GET"])
def landing():
    return render_template("landing.html", redirect_url=WEBPAGE)


@privacy_view.route("", methods=["GET"])
def privacy():
    return render_template("privacy.html")


@configure_view.route("", methods=["GET"])
def configure():
    return render_template("configure.html")
