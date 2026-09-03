from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from models import db, Notification, Post

notif_bp = Blueprint('notif_bp', __name__)

@notif_bp.route('/notifications')
@login_required
def notifications():
    user_notifs = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.id.desc()).all()
    for notif in user_notifs:
        notif.is_read = True
    db.session.commit()
    return render_template('notifications.html', notifications=user_notifs)

@notif_bp.route('/notification/click/<int:notif_id>')
@login_required
def click_notification(notif_id):
    notif = Notification.query.get_or_404(notif_id)
    if notif.user_id == current_user.id:
        return redirect(url_for('index') + f'#post-{notif.post_id}')
    return redirect(url_for('index'))
