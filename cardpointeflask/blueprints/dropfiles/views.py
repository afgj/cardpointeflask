from flask import (
    Blueprint,
    url_for,
    render_template,
    request,
    jsonify,
    current_app,
    abort,
    send_file)

from flask_login import (
    login_required
)

from werkzeug import secure_filename
import logging
import os
from .forms import DropForm

LOG = logging.getLogger(__name__)

dropfiles = Blueprint(
    'dropfiles',
    __name__,
    template_folder='templates',
    url_prefix='/dropfiles')


@dropfiles.route("/upload", methods=['GET', 'POST'])
@login_required
def upload_file():
    form = DropForm()
    if request.method == 'POST':
        files = []
        from cardpointeflask.blueprints.dropfiles.tasks\
            import process_files
        for key, f in request.files.items():
            if key.startswith('file'):
                f.save(
                    os.path.join(current_app.config['UPLOAD_FOLDER'],
                                 secure_filename(f.filename)))
                LOG.debug(f"{secure_filename(f.filename)} WRITTEN TO DISK")
                files.append(secure_filename(f.filename))
        task = process_files.delay(files)
        return jsonify({'Location': url_for('dropfiles.taskstatus',
                                            task_id=task.id)}), 202
    return render_template('dropfiles/upload.html', form=form)


@dropfiles.route("/export/<filename>", methods=['GET'])
@login_required
def export_records(filename):
    pathname = os.path.join(current_app.config['UPLOAD_FOLDER'],
                            secure_filename(filename))
    if os.path.isfile(pathname):
        return send_file(pathname)
    abort(404, description="Resource not found")


@dropfiles.route('/status/<task_id>')
@login_required
def taskstatus(task_id):
    from cardpointeflask.blueprints.dropfiles.tasks\
        import process_files
    task = process_files.AsyncResult(task_id)
    if task.state == 'PENDING':
        # job did not start yet
        response = {
            'state': task.state,
            'current': 0,
            'total': 1,
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'current': task.info.get('current', 0),
            'total': task.info.get('total', 1),
            'status': task.info.get('status', '')
        }
        if 'result' in task.info:
            response['result'] = task.info['result']
    else:
        # something went wrong in the background job
        response = {
            'state': task.state,
            'current': 1,
            'total': 1,
            'status': str(task.info),  # this is the exception raised
        }
    return jsonify(response)
