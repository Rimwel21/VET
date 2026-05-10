let resetOtpTimer;
let resetResendTimer;
let resetEmail = "";
let resetToken = "";

function openForgotPasswordModal() {
    const modal = document.getElementById('forgotPasswordModal');
    if (modal) modal.style.display = 'flex';
    document.getElementById('stepEmail').style.display = 'block';
    document.getElementById('stepOtp').style.display = 'none';
    document.getElementById('stepPassword').style.display = 'none';
    document.getElementById('resetEmail').focus();
}

function closeForgotPasswordModal() {
    const modal = document.getElementById('forgotPasswordModal');
    if (modal) modal.style.display = 'none';
    clearInterval(resetOtpTimer);
    clearInterval(resetResendTimer);
}

// STEP 1: SEND OTP
document.getElementById('sendResetOtpBtn').addEventListener('click', async () => {
    const emailInput = document.getElementById('resetEmail');
    const email = emailInput.value.trim();
    const errorMsg = document.getElementById('stepEmailError');
    const btn = document.getElementById('sendResetOtpBtn');

    if (!email) {
        errorMsg.innerText = "Please enter your email.";
        return;
    }

    btn.disabled = true;
    btn.innerText = "Sending...";
    errorMsg.innerText = "";

    try {
        const response = await fetch('/api/v1/auth/forgot-password', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]')?.content
            },
            body: JSON.stringify({ email: email })
        });
        
        if (response.ok) {
            resetEmail = email;
            document.getElementById('displayResetEmail').innerText = email;
            document.getElementById('stepEmail').style.display = 'none';
            document.getElementById('stepOtp').style.display = 'block';
            startResetCountdown(300);
            startResetResendTimer(30);
            document.querySelectorAll('.reset-otp-input')[0].focus();
        } else {
            const data = await response.json();
            errorMsg.innerText = data.message || "Failed to send OTP.";
        }
    } catch (error) {
        errorMsg.innerText = "Connection error.";
    } finally {
        btn.disabled = false;
        btn.innerText = "Send OTP";
    }
});

// STEP 2: VERIFY OTP
document.getElementById('verifyResetOtpBtn').addEventListener('click', verifyResetOtp);

async function verifyResetOtp() {
    const inputs = document.querySelectorAll('.reset-otp-input');
    const otp = Array.from(inputs).map(i => i.value).join('');
    const errorMsg = document.getElementById('stepOtpError');
    const btn = document.getElementById('verifyResetOtpBtn');

    if (otp.length < 6) return;

    btn.disabled = true;
    btn.innerText = "Verifying...";
    errorMsg.innerText = "";

    try {
        const response = await fetch('/api/v1/auth/verify-reset-otp', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]')?.content
            },
            body: JSON.stringify({ email: resetEmail, otp: otp })
        });
        
        const data = await response.json();
        
        if (data.verified) {
            resetToken = data.reset_token;
            document.getElementById('stepOtp').style.display = 'none';
            document.getElementById('stepPassword').style.display = 'block';
            document.getElementById('newPassword').focus();
        } else {
            errorMsg.innerText = data.message || "Invalid OTP";
            inputs.forEach(i => i.value = "");
            inputs[0].focus();
        }
    } catch (error) {
        errorMsg.innerText = "Connection error.";
    } finally {
        btn.disabled = false;
        btn.innerText = "Verify Code";
    }
}

// STEP 3: FINALIZE RESET
document.getElementById('finalizeResetBtn').addEventListener('click', async () => {
    const newPass = document.getElementById('newPassword').value;
    const confirmPass = document.getElementById('confirmNewPassword').value;
    const errorMsg = document.getElementById('stepPasswordError');
    const btn = document.getElementById('finalizeResetBtn');

    if (newPass.length < 8) {
        errorMsg.innerText = "Password must be at least 8 characters.";
        return;
    }

    if (newPass !== confirmPass) {
        errorMsg.innerText = "Passwords do not match.";
        return;
    }

    btn.disabled = true;
    btn.innerText = "Resetting...";
    errorMsg.innerText = "";

    try {
        const response = await fetch('/api/v1/auth/reset-password', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]')?.content
            },
            body: JSON.stringify({ 
                email: resetEmail, 
                token: resetToken,
                new_password: newPass,
                confirm_password: confirmPass
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert("Password reset successfully! You can now log in.");
            window.location.href = '/login';
        } else {
            errorMsg.innerText = data.message || "Failed to reset password.";
        }
    } catch (error) {
        errorMsg.innerText = "Connection error.";
    } finally {
        btn.disabled = false;
        btn.innerText = "Reset Password";
    }
});

// HELPERS
function startResetCountdown(duration) {
    let timer = duration, minutes, seconds;
    clearInterval(resetOtpTimer);
    resetOtpTimer = setInterval(function () {
        minutes = parseInt(timer / 60, 10);
        seconds = parseInt(timer % 60, 10);
        minutes = minutes < 10 ? "0" + minutes : minutes;
        seconds = seconds < 10 ? "0" + seconds : seconds;
        document.getElementById('resetCountdown').textContent = minutes + ":" + seconds;
        if (--timer < 0) {
            clearInterval(resetOtpTimer);
            document.getElementById('stepOtpError').innerText = "OTP expired.";
        }
    }, 1000);
}

function startResetResendTimer(duration) {
    let timer = duration;
    const btn = document.getElementById('resendResetOtpBtn');
    const span = document.getElementById('resendResetTimer');
    btn.disabled = true;
    clearInterval(resetResendTimer);
    resetResendTimer = setInterval(function () {
        span.textContent = timer;
        if (--timer < 0) {
            clearInterval(resetResendTimer);
            btn.disabled = false;
            span.parentElement.style.display = 'none';
            btn.textContent = "Resend Code";
        }
    }, 1000);
}

// Input behavior for OTP boxes
document.querySelectorAll('.reset-otp-input').forEach((input, index) => {
    input.addEventListener('input', (e) => {
        if (e.target.value.length === 1 && index < 5) {
            document.querySelectorAll('.reset-otp-input')[index + 1].focus();
        }
        if (index === 5 && e.target.value.length === 1) {
            verifyResetOtp();
        }
    });
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Backspace' && e.target.value.length === 0 && index > 0) {
            document.querySelectorAll('.reset-otp-input')[index - 1].focus();
        }
    });
});
