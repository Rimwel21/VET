import json
from flask import current_app
from pywebpush import webpush, WebPushException
from app.models.notification import PushSubscription


def send_push_notification(user_id, title, body, url="/dashboard", persist=True):
    """
    Sends a web push notification to all registered browser subscriptions of a user.
    Also saves an in-app notification record to the database if persist=True.

    Returns True if at least one push was sent successfully, False otherwise.
    """
    from app.extensions import db
    from app.models.notification import Notification
    from app.models.user import User

    # -----------------------------------------------------------------------
    # STEP 1: Always persist an in-app notification record first.
    # This ensures the user sees the message in-app even if push delivery fails.
    # -----------------------------------------------------------------------
    if persist:
        try:
            note = Notification(user_id=user_id, title=title, message=body)
            db.session.add(note)
            db.session.commit()
            current_app.logger.info(f"[PushService] Persisted in-app notification for user {user_id}.")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"[PushService] Failed to persist in-app notification: {e}")

    # -----------------------------------------------------------------------
    # STEP 2: Fetch the user record.
    # -----------------------------------------------------------------------
    user = db.session.get(User, user_id)
    if not user:
        current_app.logger.warning(f"[PushService] User {user_id} not found. Skipping push.")
        return False

    if not user.push_enabled:
        current_app.logger.info(f"[PushService] User {user_id} has push_enabled=False. Skipping push.")
        return False

    # -----------------------------------------------------------------------
    # STEP 3: Fetch all push subscriptions for this user.
    # -----------------------------------------------------------------------
    subscriptions = PushSubscription.query.filter_by(user_id=user_id).all()
    if not subscriptions:
        current_app.logger.info(f"[PushService] No push subscriptions found for user {user_id}.")
        return False

    # -----------------------------------------------------------------------
    # STEP 4: Load and validate VAPID configuration.
    # -----------------------------------------------------------------------
    vapid_private_key = current_app.config.get('VAPID_PRIVATE_KEY', '').strip()
    vapid_claims      = current_app.config.get('VAPID_CLAIMS')

    if not vapid_private_key:
        current_app.logger.error("[PushService] VAPID_PRIVATE_KEY is not configured.")
        return False

    if not vapid_claims:
        current_app.logger.error("[PushService] VAPID_CLAIMS is not configured.")
        return False

    # -----------------------------------------------------------------------
    # STEP 5: Parse and instantiate the VAPID Private Key safely.
    # Supports PEM format, raw base64url string, or raw padded base64 string.
    # -----------------------------------------------------------------------
    from py_vapid import Vapid
    vapid_obj = None

    # Try 1: Try loading as PEM format
    if "-----BEGIN" in vapid_private_key:
        try:
            vapid_obj = Vapid.from_pem(vapid_private_key.encode('utf-8'))
            current_app.logger.info("[PushService] Successfully loaded VAPID key from PEM format.")
        except Exception as e:
            current_app.logger.warning(f"[PushService] Failed to parse VAPID key as PEM: {e}")

    # Try 2: Try loading directly as a base64url string
    if not vapid_obj:
        try:
            vapid_obj = Vapid.from_string(vapid_private_key)
            current_app.logger.info("[PushService] Successfully loaded VAPID key from raw base64url string.")
        except Exception as e:
            current_app.logger.warning(f"[PushService] Failed to parse VAPID key as base64url string: {e}")

    # Try 3: Try base64 decoding manually and loading as raw bytes (with padding)
    if not vapid_obj:
        try:
            import base64
            padded = vapid_private_key + '=' * (4 - len(vapid_private_key) % 4)
            raw_bytes = base64.urlsafe_b64decode(padded)
            vapid_obj = Vapid.from_raw(raw_bytes)
            current_app.logger.info("[PushService] Successfully loaded VAPID key from base64-decoded raw bytes.")
        except Exception as e:
            current_app.logger.error(f"[PushService] All VAPID private key parsing attempts failed: {e}")
            return False

    # -----------------------------------------------------------------------
    # STEP 6: Build the notification payload JSON.
    # -----------------------------------------------------------------------
    payload = json.dumps({
        "title": title,
        "body":  body,
        "data":  {"url": url}
    })

    # -----------------------------------------------------------------------
    # STEP 7: Attempt delivery to each registered subscription endpoint.
    # -----------------------------------------------------------------------
    success = False
    for sub in subscriptions:
        if not sub.endpoint or not sub.p256dh or not sub.auth:
            current_app.logger.warning(f"[PushService] Skipping incomplete subscription id={sub.id}.")
            continue

        sub_info = {
            "endpoint": sub.endpoint,
            "keys": {
                "p256dh": sub.p256dh,
                "auth":   sub.auth
            }
        }

        try:
            webpush(
                subscription_info=sub_info,
                data=payload,
                vapid_private_key=vapid_obj,
                vapid_claims=vapid_claims
            )
            success = True
            current_app.logger.info(f"[PushService] Push delivered to user {user_id}, sub id={sub.id}.")

        except WebPushException as ex:
            status_code = None
            if hasattr(ex, 'response') and ex.response is not None:
                status_code = getattr(ex.response, 'status_code', None)

            current_app.logger.error(
                f"[PushService] WebPushException for sub id={sub.id}: {repr(ex)} | HTTP {status_code}"
            )

            # Remove expired or invalid subscriptions to keep the database table clean
            if status_code in [404, 410]:
                try:
                    db.session.delete(sub)
                    db.session.commit()
                    current_app.logger.info(f"[PushService] Removed expired subscription id={sub.id}.")
                except Exception as del_err:
                    db.session.rollback()
                    current_app.logger.error(f"[PushService] Failed to delete sub id={sub.id}: {del_err}")

        except Exception as ex:
            current_app.logger.error(f"[PushService] Unexpected error for sub id={sub.id}: {ex}")

    return success
