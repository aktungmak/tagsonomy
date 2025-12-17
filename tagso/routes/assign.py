from flask import Blueprint, request, render_template, url_for, current_app
from werkzeug.local import LocalProxy
from werkzeug.utils import redirect

assign_bp = Blueprint('assign', __name__)

gm = LocalProxy(lambda: current_app.gm)


@assign_bp.get('/assign')
def assign_get():
    selected_class_uri = request.args.get('selected_class_uri', '')
    selected_table_uri = request.args.get('selected_table_uri', '')
    return render_template("assign.html", classes=gm.get_classes(), tables=gm.get_tables(),
                           selected_class_uri=selected_class_uri, selected_table_uri=selected_table_uri)


@assign_bp.post('/assign')
def assign_post():
    class_uri = request.form.get('class_uri')
    table_uri = request.form.get('table_uri')
    gm.insert_assignment(table_uri, class_uri)
    return redirect(url_for('assign.assign_get'))
