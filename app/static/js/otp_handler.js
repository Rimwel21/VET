let otpTimer;
let resendTimer;
let currentEmail = "";

function openOtpModal(email) {
    currentEmail = email;
    document.getElementById('displayEmail').innerText = email;
    document.getElementById('otpModal').style.display = 'flex';
    document.querySelectorAll('.otp-input')[0].focus();
    startCountdown(300); // 5 minutes
    startResendTimer(30); // 30 seconds cooldown
}

function closeOtpModal() {
    document.getElementById('otpModal').style.display = 'none';
    clearInterval(otpTimer);
    clearInterval(resendTimer);
}

function startCountdown(duration) {
    let timer = duration, minutes, seconds;
    clearInterval(otpTimer);
    otpTimer = setInterval(function () {
        minutes = parseInt(timer / 60, 10);
        seconds = parseInt(timer % 60, 10);

        minutes = minutes < 10 ? "0" + minutes : minutes;
        seconds = seconds < 10 ? "0" + seconds : seconds;

        document.getElementById('countdown').textContent = minutes + ":" + seconds;

        if (--timer < 0) {
            clearInterval(otpTimer);
            document.getElementById('otpError').innerText = "OTP expired. Please resend.";
        }
    }, 1000);
}

function startResendTimer(duration) {
    let timer = duration;
    const btn = document.getElementById('resendOtpBtn');
    const span = document.getElementById('resendTimer');
    btn.disabled = true;
    
    clearInterval(resendTimer);
    resendTimer = setInterval(function () {
        span.textContent = timer;
        if (--timer < 0) {
            clearInterval(resendTimer);
            btn.disabled = false;
            span.parentElement.style.display = 'none';
            btn.textContent = "Resend Code";
        }
    }, 1000);
}

// Input behavior
document.querySelectorAll('.otp-input').forEach((input, index) => {
    input.addEventListener('input', (e) => {
        if (e.target.value.length === 1 && index < 5) {
            document.querySelectorAll('.otp-input')[index + 1].focus();
        }
        
        // Auto-submit if last digit is entered
        if (index === 5 && e.target.value.length === 1) {
            verifyOtp();
        }
    });

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Backspace' && e.target.value.length === 0 && index > 0) {
            document.querySelectorAll('.otp-input')[index - 1].focus();
        }
    });
});

async function verifyOtp() {
    const inputs = document.querySelectorAll('.otp-input');
    const otp = Array.from(inputs).map(i => i.value).join('');
    
    if (otp.length < 6) return;
    
    const btn = document.getElementById('verifyOtpBtn');
    const errorMsg = document.getElementById('otpError');
    
    btn.disabled = true;
    btn.innerText = "Verifying...";
    errorMsg.innerText = "";

    try {
        const response = await fetch('/api/v1/auth/verify-otp', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]')?.content
            },
            body: JSON.stringify({ email: currentEmail, otp: otp })
        });
        
        const data = await response.json();
        
        if (data.verified) {
            // Success! Trigger the callback
            if (window.onOtpVerified) {
                window.onOtpVerified();
            }
            closeOtpModal();
        } else {
            errorMsg.innerText = data.message || "Invalid OTP";
            btn.disabled = false;
            btn.innerText = "Verify Code";
            // Clear inputs on failure
            inputs.forEach(i => i.value = "");
            inputs[0].focus();
        }
    } catch (error) {
        errorMsg.innerText = "Connection error. Try again.";
        btn.disabled = false;
        btn.innerText = "Verify Code";
    }
}

document.getElementById('verifyOtpBtn').addEventListener('click', verifyOtp);

document.getElementById('resendOtpBtn').addEventListener('click', async () => {
    const btn = document.getElementById('resendOtpBtn');
    btn.disabled = true;
    btn.innerText = "Sending...";

    try {
        const response = await fetch('/api/v1/auth/send-otp', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]')?.content
            },
            body: JSON.stringify({ email: currentEmail })
        });
        
        if (response.ok) {
            startCountdown(300);
            startResendTimer(30);
            document.getElementById('otpError').innerText = "New OTP sent!";
            document.getElementById('otpError').style.color = "#00c9b1";
        } else {
            const data = await response.json();
            document.getElementById('otpError').innerText = data.message || "Failed to resend.";
            document.getElementById('otpError').style.color = "#ff4d4d";
            btn.disabled = false;
        }
    } catch (error) {
        document.getElementById('otpError').innerText = "Connection error.";
    }
    btn.innerText = "Resend Code";
});
