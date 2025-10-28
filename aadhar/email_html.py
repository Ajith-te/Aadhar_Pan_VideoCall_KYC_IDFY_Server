from config import Super_Agent_Mobile_Number

def video_kyc_status_email_html(user_name):
    html_body = f"""
        <html>
            <body>
                <p style="font-size: 11pt; font-family: Calibri, sans-serif; background-color: white !important; margin-top: 15px;">
                    Dear {user_name},
                </p>
                <p style="font-size: 11pt; font-family: Calibri, sans-serif; background-color: white !important; margin-top: 15px;">
                    I hope this message finds you well
                    <br><br>We regret to inform you that your video KYC was not approved due to (quality issues/ mismatch information) 
                    <br>We kindly request you to try again at your earliest convenience.
                
                    <br><br>Please ensure that you follow the guidelines carefully to avoid any issues during the verification process.
                    <br>For any assistance, please contact Veda - our super-agent assistant - +91 {Super_Agent_Mobile_Number}.
    
                    <br><br>Thank you for your understanding and cooperation
                </p>
                <p style="font-size: 11pt; font-family: Calibri, sans-serif; background-color: white !important; margin-top: 30px; margin-bottom: 20px; color: rgb(89, 35, 117);">
                    Best Regards,<br/>
                    FIA Global team <br/>
                </p>
                <p style="font-size: 11pt; font-family: Calibri, sans-serif; background-color: white !important; margin-top: 15px;">
                    <b>
                        <span style="color: rgb(104, 139, 42) !important; font-size: 12pt; font-family: inherit; padding: 0px; border: 1pt none windowtext;">Go Green. Keep it on the screen.&nbsp;</span>
                    </b>
                    <br>
                    <b>
                        <span style="color: black !important; font-size: 10pt; font-family: inherit; padding: 0px; border: 1pt none windowtext;">Disclaimer:</span>
                    </b>
                    <span style="color: black !important; font-size: 10pt; font-family: inherit; padding: 0px; border: 1pt none windowtext;">
                        This message, including any attachments, may include privileged, confidential and/or inside information. Any distribution or use of this communication by anyone other than the intended recipient is strictly prohibited and may be unlawful. If you are not the intended recipient, please notify the sender by replying to this message and then delete it from your system. Emails cannot be guaranteed to be secure or error-free as the message and any attachments could be intercepted, corrupted, lost, or amended. FIA Technology Services Private Ltd. does not accept liability for damage caused by this email or any attachments. 
                        Further please be informed that as per Company Security policy, we will never request you to disclose your Account Number, Credit and Debit Card Information, User ID, Personal Identification Number (PIN), Telephone Identification Number (TIN), Password, or any such information through e-mails or phone. Any e-mail or written communication received by you, which appears to have been sent from seeking your personal & confidential information, should not be answered but advised/informed to us.
                    </span>
                </p>
            </body>
        </html>"""
    return html_body


def video_kyc_resend_html_agent(agent_name, remarks, new_video_kyc_link, profile_id):
    html_body = f"""
        <html>
            <body>
                <p>Dear {agent_name},</p>
                <p>Unfortunately, your Video KYC has been rejected. Please find the remarks below:
                   <br><strong>Remarks: {remarks}</strong>
                </p>
                <p>You can complete your Video KYC again using the following link:
                   <br><strong>Link: <a href="{new_video_kyc_link}">{new_video_kyc_link}</a></strong>
                   <br><strong>Profile ID: {profile_id}</strong>
                </p>
                <p>If you have any questions, feel free to contact our support team.
                   <br>Thank you for your cooperation.
                </p>
                <p style="font-size: 11pt; font-family: Calibri, sans-serif; background-color: white !important; margin-top: 30px; margin-bottom: 20px; color: rgb(89, 35, 117);">
                    Best Regards,<br/>
                    Fia<br/>
                </p>
                <p style="font-size: 11pt; font-family: Calibri, sans-serif; background-color: white !important; margin-top: 15px;">
                    <b>
                        <span style="color: rgb(104, 139, 42) !important; font-size: 12pt; font-family: inherit; padding: 0px; border: 1pt none windowtext;">Go Green. Keep it on the screen.&nbsp;</span>
                    </b>
                    <br>
                    <b>
                        <span style="color: black !important; font-size: 10pt; font-family: inherit; padding: 0px; border: 1pt none windowtext;">Disclaimer:</span>
                    </b>
                    <span style="color: black !important; font-size: 10pt; font-family: inherit; padding: 0px; border: 1pt none windowtext;">
                        This message, including any attachments, may include privileged, confidential and/or inside information. Any distribution or use of this communication by anyone other than the intended recipient is strictly prohibited and may be unlawful. If you are not the intended recipient, please notify the sender by replying to this message and then delete it from your system. Emails cannot be guaranteed to be secure or error-free as the message and any attachments could be intercepted, corrupted, lost, or amended. FIA Technology Services Private Ltd. does not accept liability for damage caused by this email or any attachments. 
                        Further please be informed that as per Company Security policy, we will never request you to disclose your Account Number, Credit and Debit Card Information, User ID, Personal Identification Number (PIN), Telephone Identification Number (TIN), Password, or any such information through e-mails or phone. Any e-mail or written communication received by you, which appears to have been sent from seeking your personal & confidential information, should not be answered but advised/informed to us.
                    </span>
                </p>
            </body>
        </html>"""
    
    return html_body
