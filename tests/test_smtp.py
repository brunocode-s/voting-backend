import smtplib
from email.mime.text import MIMEText

EMAIL = "brsavvv@gmail.com"
APP_PASSWORD = "syzzxkjuagxjjjqn"

msg = MIMEText("SMTP test successful")
msg["Subject"] = "SMTP Test"
msg["From"] = EMAIL
msg["To"] = EMAIL

try:
    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)

    server.login(EMAIL, APP_PASSWORD)

    server.sendmail(EMAIL, EMAIL, msg.as_string())

    print("✅ Email sent successfully")

    server.quit()

except Exception as e:
    print("❌ SMTP Error:")
    print(e)