from flask import current_app
from flask_mail import Message
from app.extensions import mail

def send_booking_email(booking, status):
    """
    Sends a beautifully designed HTML transactional email to the client
    when their appointment status is updated to 'confirmed' (accepted) or 'cancelled'.
    """
    if not booking.email:
        current_app.logger.warning(f"Booking #{booking.id} has no email address. Skipping email alert.")
        return False

    # Set subject based on the new status
    if status == 'confirmed':
        subject = f"Appointment Confirmed! VetSync Clinic - {booking.pet_name}"
        status_text = "Confirmed"
        status_color = "#16a34a" # Green
        title_text = "Your Appointment is Confirmed!"
        body_text = f"Great news! Your booking for <strong>{booking.pet_name}</strong> has been accepted by our clinical team. We are looking forward to seeing you."
    elif status == 'cancelled':
        subject = f"Appointment Cancelled - VetSync Clinic - {booking.pet_name}"
        status_text = "Cancelled"
        status_color = "#dc2626" # Red
        title_text = "Appointment Cancellation Notice"
        body_text = f"We would like to notify you that your booking for <strong>{booking.pet_name}</strong> has been cancelled. If you need to reschedule or have any questions, please contact our support team or book a new slot online."
    else:
        # We only send emails for confirmed or cancelled status updates
        return False

    service_name = booking.service_ref.name if booking.service_ref else "Veterinary Consultation"
    formatted_date = booking.date.strftime('%B %d, %Y')

    # Premium branded HTML Email template
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{subject}</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #f0f7ff;
                margin: 0;
                padding: 0;
                color: #1a202c;
            }}
            .email-container {{
                max-width: 600px;
                margin: 40px auto;
                background-color: #ffffff;
                border-radius: 16px;
                box-shadow: 0 12px 32px rgba(26, 60, 143, 0.08);
                overflow: hidden;
                border: 1px solid #d9e6f7;
            }}
            .email-header {{
                background: linear-gradient(135deg, #1a3c8f 0%, #1e5bbf 100%);
                padding: 30px 40px;
                text-align: center;
                color: #ffffff;
            }}
            .email-header h1 {{
                margin: 0;
                font-size: 24px;
                font-weight: 800;
                letter-spacing: 0.5px;
            }}
            .email-body {{
                padding: 40px;
            }}
            .greeting {{
                font-size: 18px;
                font-weight: 700;
                color: #1a3c8f;
                margin-top: 0;
                margin-bottom: 16px;
            }}
            .message-text {{
                font-size: 15px;
                line-height: 1.6;
                color: #4a5568;
                margin-bottom: 30px;
            }}
            .details-card {{
                background-color: #f8fbff;
                border: 1.5px solid #d9e6f7;
                border-radius: 12px;
                padding: 24px;
                margin-bottom: 30px;
            }}
            .details-title {{
                font-size: 16px;
                font-weight: 800;
                color: #1a3c8f;
                margin-top: 0;
                margin-bottom: 16px;
                border-bottom: 1px solid #d9e6f7;
                padding-bottom: 8px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            .detail-row {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 12px;
                font-size: 14px;
            }}
            .detail-row:last-child {{
                margin-bottom: 0;
            }}
            .detail-label {{
                font-weight: 700;
                color: #718096;
            }}
            .detail-value {{
                font-weight: 800;
                color: #1a202c;
                text-align: right;
            }}
            .status-badge {{
                display: inline-block;
                padding: 4px 12px;
                border-radius: 999px;
                color: #ffffff;
                font-size: 12px;
                font-weight: 800;
                text-transform: uppercase;
                background-color: {status_color};
            }}
            .footer {{
                background-color: #f8fbff;
                padding: 24px 40px;
                text-align: center;
                font-size: 12px;
                color: #a0aec0;
                border-top: 1px solid #d9e6f7;
            }}
            .footer a {{
                color: #1e5bbf;
                text-decoration: none;
                font-weight: 700;
            }}
        </style>
    </head>
    <body>
        <div class="email-container">
            <div class="email-header">
                <h1>{title_text}</h1>
            </div>
            <div class="email-body">
                <div class="greeting">Hi {booking.name},</div>
                <div class="message-text">
                    {body_text}
                </div>
                
                <div class="details-card">
                    <div class="details-title">Appointment Summary</div>
                    <div class="detail-row">
                        <span class="detail-label">Pet Name:</span>
                        <span class="detail-value">{booking.pet_name} ({booking.pet_type})</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Service:</span>
                        <span class="detail-value">{service_name}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Date:</span>
                        <span class="detail-value">{formatted_date}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Time Slot:</span>
                        <span class="detail-value">{booking.slot}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Status:</span>
                        <span class="detail-value">
                            <span class="status-badge">{status_text}</span>
                        </span>
                    </div>
                </div>
            </div>
            <div class="footer">
                This is an automated clinical notification from <strong>VetSync</strong>.<br>
                For support, visit <a href="#">vetsync.com</a> or reply to this email.
            </div>
        </div>
    </body>
    </html>
    """

    msg = Message(
        subject=subject,
        sender=current_app.config.get('MAIL_USERNAME'),
        recipients=[booking.email]
    )
    msg.html = html_content
    
    # Text-only fallback for email clients that do not support HTML
    msg.body = f"Hi {booking.name},\n\n" \
               f"Your appointment for {booking.pet_name} ({service_name}) on {formatted_date} at {booking.slot} is {status_text}.\n\n" \
               f"Thank you,\nVetSync Clinic"

    try:
        mail.send(msg)
        current_app.logger.info(f"Successfully sent booking status email for Booking #{booking.id} ({status}) to {booking.email}")
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send booking status email for Booking #{booking.id} to {booking.email}: {e}")
        return False
